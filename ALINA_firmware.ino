/* ============================================================================
   ALINA - Firmware ESP32  v2.0
   Monitoreo y corrección postural con biofeedback háptico + WiFi + WebSocket

   BOTÓN (GPIO 13):
     - Pulsación corta x2 (≥5s entre ellas) → calibración postural del usuario
     - Mantener 5s                           → modo pairing WiFi (Captive Portal)
     - Mantener 20s                          → recalibración de hardware (offsets IMU)

   SD (/config.json):
     - device_name, haptic_intensity, last_calibration_at
     (el WiFi lo guarda WiFiManager automáticamente en NVS)

   WEBSOCKET (puerto 81):
     Mensajes que recibe (app → ESP):
       {"cmd":"start_session"}
       {"cmd":"stop_session"}
       {"cmd":"calibrate"}
       {"cmd":"set_config","device_name":"...","haptic_intensity":60}
       {"cmd":"wifi_reset"}

     Mensajes que envía (ESP → app):
       {"type":"status","calibrated":true,"imu_t1":true,"imu_t12":true,"imu_rpsis":true}
       {"type":"posture","t1_pitch":1.2,"t1_roll":0.3,"t12_pitch":0.8,"t12_roll":0.1,"rpsis_pitch":0.5,"rpsis_roll":0.2}
       {"type":"alert","source":"T12","count":5}
       {"type":"session_end","duracion_min":45.0,"alertas_hapticas":3,"min_buena":38.0,"min_mala":7.0}
   ============================================================================ */

#include <Wire.h>
#include <MPU6500_WE.h>
#include <SPI.h>
#include <SD.h>
#include <WiFi.h>
#include <WiFiManager.h>
#include <WebSocketsServer.h>
#include <ArduinoJson.h>
#include <ESPmDNS.h>
#include "driver/gpio.h"

// ─── Pines ───────────────────────────────────────────────────────────────────
const int SDA_PIN    = 21;  const int SCL_PIN    = 22;
const int SDA_RPSIS  = 25;  const int SCL_RPSIS  = 26;
const int SD_CS      = 5;
const int BOTON_PIN  = 13;
const int M1_PIN = 14, M2_PIN = 27, M3_PIN = 32, M4_PIN = 33;

// ─── Direcciones I2C ─────────────────────────────────────────────────────────
const int ADDR_T12 = 0x68, ADDR_T1 = 0x69, ADDR_RPSIS = 0x68;

// ─── Parámetros de postura ───────────────────────────────────────────────────
const float T1_PITCH_MIN = -23.0, T1_ROLL_LIM = 10.0;
const float T12_PITCH_MIN = -10.0, T12_ROLL_LIM = 5.0;

// ─── Parámetros de ventana ───────────────────────────────────────────────────
const unsigned long VENTANA_MS = 15000;
const float         PROP_UMBRAL = 0.70;
const unsigned long VIBRA_MS   = 1000;
const unsigned long PERIODO_MS = 100;

// ─── Tiempos del botón ───────────────────────────────────────────────────────
const unsigned long CALIB_MIN_MS  =  5000;
const unsigned long WIFI_RESET_MS =  5000;
const unsigned long HW_CALIB_MS   = 20000;

// ─── IMUs ────────────────────────────────────────────────────────────────────
MPU6500_WE mpuT12   = MPU6500_WE(&Wire,  ADDR_T12);
MPU6500_WE mpuT1    = MPU6500_WE(&Wire,  ADDR_T1);
MPU6500_WE mpuRPSIS = MPU6500_WE(&Wire1, ADDR_RPSIS);
bool imuT12OK = false, imuT1OK = false, imuRPSISok = false;

// ─── WebSocket ───────────────────────────────────────────────────────────────
WebSocketsServer webSocket = WebSocketsServer(81);
int wsClient = -1;

// ─── Timer de muestreo ───────────────────────────────────────────────────────
hw_timer_t *timerMuestreo = NULL;
volatile bool tickMuestreo = false;
void IRAM_ATTR onTimer() { tickMuestreo = true; }

// ─── Botón ───────────────────────────────────────────────────────────────────
volatile bool botonEvento = false;
volatile unsigned long ultimaPulsacionISR = 0;
void IRAM_ATTR onBoton() {
  unsigned long ahora = millis();
  if (ahora - ultimaPulsacionISR > 250) {
    ultimaPulsacionISR = ahora;
    botonEvento = true;
  }
}

// ─── Estado calibración postural ─────────────────────────────────────────────
enum EstadoCalib { SIN_CALIBRAR, ESPERANDO_FIN, CALIBRADO };
EstadoCalib estadoCalib = SIN_CALIBRAR;
unsigned long tInicioCalib = 0;
float refT1_pitch = 0, refT1_roll = 0;
float refT12_pitch = 0, refT12_roll = 0;

// ─── Ventanas de evaluación ──────────────────────────────────────────────────
unsigned long tInicioVentanaT1 = 0, tInicioVentanaT12 = 0;
unsigned int totalT1 = 0, malasT1 = 0;
unsigned int totalT12 = 0, malasT12 = 0;

// ─── Sesión activa ───────────────────────────────────────────────────────────
enum EstadoSesion { SESION_IDLE, SESION_RUNNING, SESION_PAUSED };
EstadoSesion estadoSesion = SESION_IDLE;
unsigned long tInicioSesion  = 0;   // ms cuando arrancó la sesión
unsigned long tFinSesion     = 0;   // ms cuando se detuvo
unsigned long tUltimoMuestreo = 0;
unsigned int  alertasHapticas = 0;
float minBuena = 0.0, minMala = 0.0;

// ─── Vibración ───────────────────────────────────────────────────────────────
bool vibrando = false;
unsigned long tFinVibra = 0;

// ─── SD y config ─────────────────────────────────────────────────────────────
bool    sdDisponible     = false;
String  cfgDeviceName    = "ALINA Dispositivo";
int     cfgHapticIntensity = 60;
String  cfgLastCalibAt   = "";

// ─── Botón pulsación larga ───────────────────────────────────────────────────
unsigned long tBotonPresionado = 0;
bool botonEstabaPresionado = false, accionLargaHecha = false;

// =============================================================================
// SD: config.json
// =============================================================================

void guardarConfig() {
  if (!sdDisponible) return;
  if (SD.exists("/config.json")) SD.remove("/config.json");
  File f = SD.open("/config.json", FILE_WRITE);
  if (!f) return;
  StaticJsonDocument<256> doc;
  doc["device_name"]      = cfgDeviceName;
  doc["haptic_intensity"] = cfgHapticIntensity;
  doc["last_calib_at"]    = cfgLastCalibAt;
  serializeJson(doc, f);
  f.close();
  Serial.println("Config guardada en SD.");
}

void cargarConfig() {
  if (!sdDisponible || !SD.exists("/config.json")) return;
  File f = SD.open("/config.json");
  if (!f) return;
  StaticJsonDocument<256> doc;
  if (!deserializeJson(doc, f)) {
    cfgDeviceName      = doc["device_name"]     | "ALINA Dispositivo";
    cfgHapticIntensity = doc["haptic_intensity"] | 60;
    cfgLastCalibAt     = doc["last_calib_at"]    | "";
  }
  f.close();
  Serial.println("Config cargada de SD.");
}

// =============================================================================
// SD: offsets HW y calibración postural
// =============================================================================

void guardarOffsetsHW() {
  if (!sdDisponible) return;
  if (SD.exists("/offsets_hw.txt")) SD.remove("/offsets_hw.txt");
  File f = SD.open("/offsets_hw.txt", FILE_WRITE);
  if (!f) return;
  f.println("# Offsets HW ALINA — generados automaticamente");
  f.close();
  Serial.println("Offsets HW guardados.");
}

bool cargarOffsetsHW() {
  if (!sdDisponible) return false;
  return SD.exists("/offsets_hw.txt");
}

void guardarCalibracionSD() {
  if (!sdDisponible) return;
  if (SD.exists("/calibracion.txt")) SD.remove("/calibracion.txt");
  File f = SD.open("/calibracion.txt", FILE_WRITE);
  if (!f) return;
  f.println("# Calibracion postural ALINA");
  f.print("refT1_pitch=");  f.println(refT1_pitch, 2);
  f.print("refT1_roll=");   f.println(refT1_roll, 2);
  f.print("refT12_pitch="); f.println(refT12_pitch, 2);
  f.print("refT12_roll=");  f.println(refT12_roll, 2);
  f.close();
  cfgLastCalibAt = String(millis());
  guardarConfig();
  Serial.println("Calibracion postural guardada.");
}

bool cargarCalibracionSD() {
  if (!sdDisponible || !SD.exists("/calibracion.txt")) return false;
  File f = SD.open("/calibracion.txt");
  if (!f) return false;
  while (f.available()) {
    String linea = f.readStringUntil('\n'); linea.trim();
    if (linea.startsWith("#")) continue;
    int eq = linea.indexOf('=');
    if (eq < 0) continue;
    String key = linea.substring(0, eq);
    float  val = linea.substring(eq + 1).toFloat();
    if (key == "refT1_pitch")  refT1_pitch  = val;
    if (key == "refT1_roll")   refT1_roll   = val;
    if (key == "refT12_pitch") refT12_pitch = val;
    if (key == "refT12_roll")  refT12_roll  = val;
  }
  f.close();
  return true;
}

// =============================================================================
// WebSocket — enviar
// =============================================================================

void wsSend(const String &msg) {
  if (wsClient >= 0) webSocket.sendTXT(wsClient, msg);
}

void wsEnviarStatus() {
  StaticJsonDocument<128> doc;
  doc["type"]      = "status";
  doc["calibrated"] = (estadoCalib == CALIBRADO);
  doc["imu_t1"]    = imuT1OK;
  doc["imu_t12"]   = imuT12OK;
  doc["imu_rpsis"] = imuRPSISok;
  String out; serializeJson(doc, out); wsSend(out);
}

void wsEnviarPostura(float t1p, float t1r, float t12p, float t12r, float rp, float rr) {
  StaticJsonDocument<192> doc;
  doc["type"]        = "posture";
  doc["t1_pitch"]    = t1p;   doc["t1_roll"]    = t1r;
  doc["t12_pitch"]   = t12p;  doc["t12_roll"]   = t12r;
  doc["rpsis_pitch"] = rp;    doc["rpsis_roll"]  = rr;
  String out; serializeJson(doc, out); wsSend(out);
}

void wsEnviarAlerta(const char* fuente) {
  StaticJsonDocument<64> doc;
  doc["type"]  = "alert";
  doc["source"] = fuente;
  doc["count"] = alertasHapticas;
  String out; serializeJson(doc, out); wsSend(out);
}

void wsEnviarFinSesion() {
  if (estadoSesion == SESION_IDLE) return;
  tFinSesion = millis();
  float durMin = (tFinSesion - tInicioSesion) / 60000.0;
  StaticJsonDocument<192> doc;
  doc["type"]             = "session_end";
  doc["started_at_ms"]    = tInicioSesion;   // ms desde arranque del ESP
  doc["ended_at_ms"]      = tFinSesion;
  doc["duracion_min"]     = durMin;
  doc["alertas_hapticas"] = alertasHapticas;
  doc["min_buena"]        = minBuena;
  doc["min_mala"]         = minMala;
  String out; serializeJson(doc, out); wsSend(out);
  Serial.println("session_end enviado a la app.");
}

// =============================================================================
// WebSocket — recibir
// =============================================================================

void procesarComando(const String &msg) {
  StaticJsonDocument<256> doc;
  if (deserializeJson(doc, msg)) return;
  const char* cmd = doc["cmd"];
  if (!cmd) return;

  if (strcmp(cmd, "start_session") == 0) {
    estadoSesion    = SESION_RUNNING;
    tInicioSesion   = millis();
    tUltimoMuestreo = millis();
    alertasHapticas = 0;
    minBuena = minMala = 0.0;
    // Confirmar estado a la app
    StaticJsonDocument<64> ack;
    ack["type"]  = "session_status";
    ack["state"] = "running";
    ack["started_at_ms"] = tInicioSesion;
    String aout; serializeJson(ack, aout); wsSend(aout);
    Serial.println("Sesión iniciada.");

  } else if (strcmp(cmd, "pause_session") == 0) {
    if (estadoSesion == SESION_RUNNING) {
      estadoSesion = SESION_PAUSED;
      StaticJsonDocument<32> ack;
      ack["type"]  = "session_status";
      ack["state"] = "paused";
      String aout; serializeJson(ack, aout); wsSend(aout);
      Serial.println("Sesión pausada.");
    }

  } else if (strcmp(cmd, "resume_session") == 0) {
    if (estadoSesion == SESION_PAUSED) {
      estadoSesion    = SESION_RUNNING;
      tUltimoMuestreo = millis();   // resetear para no acumular el tiempo pausado
      StaticJsonDocument<32> ack;
      ack["type"]  = "session_status";
      ack["state"] = "running";
      String aout; serializeJson(ack, aout); wsSend(aout);
      Serial.println("Sesión reanudada.");
    }

  } else if (strcmp(cmd, "stop_session") == 0) {
    wsEnviarFinSesion();
    estadoSesion = SESION_IDLE;
    // Confirmar
    StaticJsonDocument<32> ack;
    ack["type"]  = "session_status";
    ack["state"] = "idle";
    String aout; serializeJson(ack, aout); wsSend(aout);

  } else if (strcmp(cmd, "calibrate") == 0) {
    xyzFloat aT1 = mpuT1.getAngles(), aT12 = mpuT12.getAngles();
    refT1_pitch = aT1.y; refT1_roll = aT1.x;
    refT12_pitch = aT12.y; refT12_roll = aT12.x;
    estadoCalib = CALIBRADO;
    guardarCalibracionSD();
    wsEnviarStatus();
    Serial.println("Calibración ejecutada desde la app.");

  } else if (strcmp(cmd, "set_config") == 0) {
    if (doc.containsKey("device_name"))       cfgDeviceName       = doc["device_name"].as<String>();
    if (doc.containsKey("haptic_duration_ms")) cfgHapticIntensity = doc["haptic_duration_ms"];
    guardarConfig();
    Serial.println("Config actualizada desde la app.");

  } else if (strcmp(cmd, "test_vibration") == 0) {
    // Probar vibración con la duración actual guardada en config
    // El valor llega como haptic_duration_ms desde la app
    unsigned long durMs = doc["haptic_duration_ms"] | (unsigned long)VIBRA_MS;
    dispararVibracion(true, true);   // todos los motores
    // Sobreescribir el timer para usar la duración del test
    tFinVibra = millis() + durMs;
    Serial.printf("Test vibración: %lu ms\n", durMs);

  } else if (strcmp(cmd, "wifi_reset") == 0) {
    Serial.println("Reset WiFi desde la app. Reiniciando en modo Captive Portal...");
    WiFiManager wm;
    wm.resetSettings();
    delay(500);
    ESP.restart();
  }
}

void webSocketEvent(uint8_t num, WStype_t type, uint8_t *payload, size_t length) {
  if (type == WStype_CONNECTED) {
    wsClient = num;
    Serial.printf("WS cliente %d conectado\n", num);
    wsEnviarStatus();
  } else if (type == WStype_DISCONNECTED) {
    if (wsClient == num) wsClient = -1;
    Serial.printf("WS cliente %d desconectado\n", num);
  } else if (type == WStype_TEXT) {
    procesarComando(String((char*)payload));
  }
}

// =============================================================================
// Motores y clasificadores
// =============================================================================

void apagarMotores() {
  gpio_set_level((gpio_num_t)M1_PIN, 0); gpio_set_level((gpio_num_t)M2_PIN, 0);
  gpio_set_level((gpio_num_t)M3_PIN, 0); gpio_set_level((gpio_num_t)M4_PIN, 0);
}

void dispararVibracion(bool grupoT12, bool grupoT1) {
  if (grupoT12) { gpio_set_level((gpio_num_t)M1_PIN, 1); gpio_set_level((gpio_num_t)M2_PIN, 1); }
  if (grupoT1)  { gpio_set_level((gpio_num_t)M3_PIN, 1); gpio_set_level((gpio_num_t)M4_PIN, 1); }
  vibrando = true;
  // Usar duración configurada por el usuario (cfgHapticIntensity), con VIBRA_MS como fallback
  unsigned long dur = (cfgHapticIntensity > 0) ? (unsigned long)cfgHapticIntensity : VIBRA_MS;
  tFinVibra = millis() + dur;
  alertasHapticas++;
}

bool malaPosturaT1(float p, float r)  { return (p < T1_PITCH_MIN)  || (fabs(r) > T1_ROLL_LIM);  }
bool malaPosturaT12(float p, float r) { return (p < T12_PITCH_MIN) || (fabs(r) > T12_ROLL_LIM); }

// =============================================================================
// Calibración por botón
// =============================================================================

void procesarBoton(float t1p, float t1r, float t12p, float t12r) {
  unsigned long ahora = millis();
  if (estadoCalib == SIN_CALIBRAR || estadoCalib == CALIBRADO) {
    estadoCalib  = ESPERANDO_FIN;
    tInicioCalib = ahora;
    Serial.println("Calibración: mantené la postura y pulsá de nuevo (≥5s).");
  } else if (estadoCalib == ESPERANDO_FIN) {
    if (ahora - tInicioCalib >= CALIB_MIN_MS) {
      refT1_pitch = t1p; refT1_roll = t1r;
      refT12_pitch = t12p; refT12_roll = t12r;
      estadoCalib = CALIBRADO;
      guardarCalibracionSD();
      wsEnviarStatus();
      Serial.println("Calibración postural completada.");
    } else {
      Serial.println("Muy pronto — esperá 5s entre pulsaciones.");
    }
  }
}

// =============================================================================
// SETUP
// =============================================================================

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("=== ALINA Firmware v2.0 ===");

  // Motores
  for (int p : {M1_PIN, M2_PIN, M3_PIN, M4_PIN}) {
    gpio_reset_pin((gpio_num_t)p);
    gpio_set_direction((gpio_num_t)p, GPIO_MODE_OUTPUT);
  }
  apagarMotores();

  // Botón
  pinMode(BOTON_PIN, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(BOTON_PIN), onBoton, FALLING);

  // I2C
  Wire.begin(SDA_PIN, SCL_PIN);
  Wire1.begin(SDA_RPSIS, SCL_RPSIS);

  // IMUs
  imuT12OK   = mpuT12.init();
  imuT1OK    = mpuT1.init();
  imuRPSISok = mpuRPSIS.init();
  if (!imuT12OK)   Serial.println("WARN: T12 no responde");
  if (!imuT1OK)    Serial.println("WARN: T1  no responde");
  if (!imuRPSISok) Serial.println("WARN: RPSIS no responde");

  // microSD
  if (SD.begin(SD_CS)) {
    sdDisponible = true;
    Serial.println("microSD OK.");
    cargarConfig();
  } else {
    Serial.println("WARN: microSD no disponible.");
  }

  // Offsets HW
  if (sdDisponible && cargarOffsetsHW()) {
    Serial.println("Offsets HW encontrados. No recalibro.");
  } else {
    Serial.println("Calculando offsets HW (quieto 3s)...");
    delay(3000);
    if (imuT12OK)   mpuT12.autoOffsets();
    if (imuT1OK)    mpuT1.autoOffsets();
    if (imuRPSISok) mpuRPSIS.autoOffsets();
    if (sdDisponible) guardarOffsetsHW();
  }

  // Settings MPU
  MPU6500_WE* todos[] = {&mpuT12, &mpuT1, &mpuRPSIS};
  for (int i = 0; i < 3; i++) {
    todos[i]->setSampleRateDivider(5);
    todos[i]->setAccRange(MPU6500_ACC_RANGE_2G);
    todos[i]->setGyrRange(MPU6500_GYRO_RANGE_250);
    todos[i]->enableGyrDLPF();
    todos[i]->setGyrDLPF(MPU6500_DLPF_6);
  }

  // Calibración postural
  if (sdDisponible && cargarCalibracionSD()) {
    estadoCalib = CALIBRADO;
    Serial.println("Calibración postural cargada de SD.");
  }

  // WiFiManager — Captive Portal si no hay credenciales guardadas
  WiFiManager wm;
  wm.setConfigPortalTimeout(180);
  if (!wm.autoConnect("ALINA-Setup")) {
    Serial.println("Sin WiFi. Reiniciando...");
    delay(3000);
    ESP.restart();
  }
  Serial.print("WiFi OK. IP: ");
  Serial.println(WiFi.localIP());

  // mDNS — accesible como alina.local en la red
  if (MDNS.begin("alina")) {
    Serial.println("mDNS OK. Dispositivo accesible como alina.local");
  } else {
    Serial.println("WARN: mDNS no pudo iniciarse.");
  }

  // WebSocket
  webSocket.begin();
  webSocket.onEvent(webSocketEvent);
  Serial.println("WebSocket en puerto 81.");

  // Timer
  timerMuestreo = timerBegin(1000000);
  timerAttachInterrupt(timerMuestreo, &onTimer);
  timerAlarm(timerMuestreo, PERIODO_MS * 1000, true, 0);

  tInicioVentanaT1 = tInicioVentanaT12 = millis();
  Serial.println("Sistema listo.");
}

// =============================================================================
// LOOP
// =============================================================================

void loop() {
  unsigned long ahora = millis();
  webSocket.loop();

  // ── 0) Pulsación larga del botón ─────────────────────────────────────────
  bool botonAhora = (digitalRead(BOTON_PIN) == LOW);
  if (botonAhora) {
    if (!botonEstabaPresionado) {
      tBotonPresionado = ahora;
      accionLargaHecha = false;
    } else if (!accionLargaHecha) {
      unsigned long dur = ahora - tBotonPresionado;
      if (dur >= HW_CALIB_MS) {
        Serial.println(">> Recalibrando HW (20s)...");
        if (imuT12OK)   mpuT12.autoOffsets();
        if (imuT1OK)    mpuT1.autoOffsets();
        if (imuRPSISok) mpuRPSIS.autoOffsets();
        if (sdDisponible) guardarOffsetsHW();
        accionLargaHecha = true;
        Serial.println(">> Recalibración HW lista.");
      } else if (dur >= WIFI_RESET_MS) {
        Serial.println(">> Reset WiFi (5s). Entrando en Captive Portal...");
        WiFiManager wm;
        wm.resetSettings();
        accionLargaHecha = true;
        delay(500);
        ESP.restart();
      }
    }
  }
  botonEstabaPresionado = botonAhora;

  // ── 1) Pulsación corta → calibración postural ────────────────────────────
  if (botonEvento && !botonAhora) {
    botonEvento = false;
    xyzFloat aT1 = mpuT1.getAngles(), aT12 = mpuT12.getAngles();
    procesarBoton(aT1.y, aT1.x, aT12.y, aT12.x);
  }

  // ── 2) Apagar motores ────────────────────────────────────────────────────
  if (vibrando && ahora >= tFinVibra) {
    apagarMotores();
    vibrando = false;
  }

  // ── 3) Tick de muestreo ──────────────────────────────────────────────────
  if (tickMuestreo) {
    tickMuestreo = false;
    xyzFloat aT1    = imuT1OK    ? mpuT1.getAngles()    : xyzFloat{0,0,0};
    xyzFloat aT12   = imuT12OK   ? mpuT12.getAngles()   : xyzFloat{0,0,0};
    xyzFloat aRPSIS = imuRPSISok ? mpuRPSIS.getAngles() : xyzFloat{0,0,0};

    float t1p  = aT1.y  - refT1_pitch,  t1r  = aT1.x  - refT1_roll;
    float t12p = aT12.y - refT12_pitch, t12r = aT12.x - refT12_roll;

    // Enviar postura al WebSocket (5 Hz)
    if (wsClient >= 0 && estadoCalib == CALIBRADO && estadoSesion == SESION_RUNNING) {
      static unsigned long ultimoWS = 0;
      if (ahora - ultimoWS > 200) {
        wsEnviarPostura(t1p, t1r, t12p, t12r, aRPSIS.y, aRPSIS.x);
        ultimoWS = ahora;
      }
    }

    // Acumular min_buena / min_mala
    if (estadoSesion == SESION_RUNNING && estadoCalib == CALIBRADO) {
      float dt = (ahora - tUltimoMuestreo) / 60000.0;
      tUltimoMuestreo = ahora;
      if (malaPosturaT1(t1p, t1r) || malaPosturaT12(t12p, t12r)) minMala  += dt;
      else                                                          minBuena += dt;
    }

    // Contadores de ventana
    if (estadoCalib == CALIBRADO) {
      totalT1++;  if (malaPosturaT1(t1p, t1r))   malasT1++;
      totalT12++; if (malaPosturaT12(t12p, t12r)) malasT12++;
    }

    // Debug serial (cada 500ms)
    static unsigned long ultimoPrint = 0;
    if (estadoCalib == CALIBRADO && ahora - ultimoPrint > 500) {
      ultimoPrint = ahora;
      Serial.printf("T1 P:%.1f R:%.1f | T12 P:%.1f R:%.1f | RPSIS P:%.1f R:%.1f\n",
        t1p, t1r, t12p, t12r, aRPSIS.y, aRPSIS.x);
    }
  }

  // ── 4) Cierre de ventanas ────────────────────────────────────────────────
  if (estadoCalib == CALIBRADO && (ahora - tInicioVentanaT12 >= VENTANA_MS)) {
    if (totalT12 > 0 && (float)malasT12 / totalT12 > PROP_UMBRAL) {
      dispararVibracion(true, false);
      wsEnviarAlerta("T12");
      Serial.printf("[T12] %.0f%% mala → vibración\n", 100.0 * malasT12 / totalT12);
    }
    tInicioVentanaT12 = ahora; totalT12 = 0; malasT12 = 0;
  }
  if (estadoCalib == CALIBRADO && (ahora - tInicioVentanaT1 >= VENTANA_MS)) {
    if (totalT1 > 0 && (float)malasT1 / totalT1 > PROP_UMBRAL) {
      dispararVibracion(false, true);
      wsEnviarAlerta("T1");
      Serial.printf("[T1 ] %.0f%% mala → vibración\n", 100.0 * malasT1 / totalT1);
    }
    tInicioVentanaT1 = ahora; totalT1 = 0; malasT1 = 0;
  }
}
