/* ============================================================================
   ALINA - Firmware ESP32  v2.1
   Monitoreo y corrección postural con biofeedback háptico + WiFi + WebSocket

   BOTÓN (GPIO 13):
     - Pulsación corta x2 (≥5s entre ellas) → calibración postural del usuario
     - Mantener 5s                           → modo pairing WiFi (Captive Portal)
     - Mantener 20s                          → borra TODO de la microSD
                                               (offsets HW + calibración + config)

   FLUJO DE CALIBRACIÓN
     1) Offsets HW (una sola vez, con la PC por cable y viendo el serial):
        - Sensores quietos y planos 3s → se calculan offsets y se GUARDAN en SD
          (/offsets_hw.txt) con sus VALORES NUMÉRICOS reales.
        - En cada arranque posterior se RECARGAN esos valores y NO se recalcula.
        - Solo se borran apretando el botón 20s.
     2) Calibración por individuo (postura de referencia):
        - 1ra pulsación → arranca, hay que esperar ≥5s manteniendo la postura.
        - 2da pulsación → si pasaron ≥5s, se guarda la referencia en SD.
          (queda guardada hasta que el usuario recalibre)
        - Para recalibrar: 1ra pulsación borra la vieja y arranca una nueva.
     - En el PRIMER uso el dispositivo no clasifica/vibra hasta tener una
       calibración por individuo hecha. Una vez guardada, al prender con batería
       (sin USB) la calibración ya está en la SD y funciona solo.

   SD:
     /offsets_hw.txt  → offsets numéricos de cada IMU (no se borra salvo botón 20s)
     /calibracion.txt → referencia postural por individuo
     /config.json     → preferencias del usuario (nombre, intensidad háptica)

   WEBSOCKET (puerto 81):
     Recibe: start_session, pause_session, resume_session, stop_session,
             calibrate, set_config, test_vibration, wifi_reset
     Envía:  status, posture, alert, session_status, session_end
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
#include "Adafruit_MAX1704X.h"


// ─── Pines ───────────────────────────────────────────────────────────────────
const int SDA_PIN    = 21;  const int SCL_PIN    = 22;
const int SDA_RPSIS  = 25;  const int SCL_RPSIS  = 26;
const int SD_CS      = 5;
const int BOTON_PIN  = 13;
const int M1_PIN = 14, M2_PIN = 27, M3_PIN = 32, M4_PIN = 33;
const int LED_PIN = 2;   // LED onboard: titila en calibración
const int BOOT_BTN_PIN = 0;   // botón BOOT del ESP32: mantener 5s = reset WiFi + portal

// ─── NUEVO: buzzer y LEDs de estado ──────────────────────────────────────────
const int BUZZER_PIN    = 17;   // buzzer activo (BZ1) — suena en calibración
const int LED_VERDE_PIN = 16;   // D1 verde: fijo = dispositivo encendido
const int LED_ROJO_PIN  = 4;    // D2 rojo: RESERVADO para batería baja (MAX1704x, aún no integrado)

// ─── Direcciones I2C ─────────────────────────────────────────────────────────
const int ADDR_T12 = 0x68, ADDR_T1 = 0x69, ADDR_RPSIS = 0x68;

// ─── Umbrales de postura (NUEVOS) ────────────────────────────────────────────
// T1:  mala si  pitch < -11.2   O   roll > 22.4   O   roll < -22.4
// T12: mala si  pitch < -4.5    (el roll de T12 se mide pero NO clasifica)
const float T1_PITCH_MIN  = -11.2;
const float T1_ROLL_LIM   =  22.4;   // se usa como |roll| > 22.4
const float T12_PITCH_MIN =  -4.5; /// CORREGIR ES +4.5 no se porque 

// ─── Parámetros de ventana (NUEVOS) ──────────────────────────────────────────
// Ventana DESLIZANTE de 30s, evaluación cada 15s, umbral de proporción 60%.
const unsigned long VENTANA_MS    = 30000;  // ventana deslizante analizada
const unsigned long EVAL_CADA_MS  = 15000;  // cada cuánto se evalúa y (quizá) vibra
const float         PROP_UMBRAL   = 0.60;   // 60%
const unsigned long PERIODO_MS    = 100;    // muestreo 10 Hz
const unsigned long VIBRA_MS      = 1000;   // 1 s de vibración (fallback)

// Buffer circular: 30s a 10Hz = 300 muestras. Guarda mala/buena por punto.

const int BUF_N = (int)(VENTANA_MS / PERIODO_MS);   // 300
bool bufT12p[BUF_N];      // pitch T12 malo      → M1+M2
bool bufT1p[BUF_N];       // pitch T1 malo       → M3+M4
bool bufT1rNeg[BUF_N];    // roll T1 < -22.4     → M3+M1
bool bufT1rPos[BUF_N];    // roll T1 > +22.4     → M4+M2
int  bufIdx = 0;        // posición de escritura
int  bufLlenado = 0;    // cuántas muestras válidas hay (hasta BUF_N)

// ─── Tiempos del botón ───────────────────────────────────────────────────────
const unsigned long CALIB_MIN_MS  =  5000;
const unsigned long WIFI_RESET_MS =  5000;
const unsigned long HW_WIPE_MS    = 20000;

// ─── IMUs ────────────────────────────────────────────────────────────────────
MPU6500_WE mpuT12   = MPU6500_WE(&Wire,  ADDR_T12);
MPU6500_WE mpuT1    = MPU6500_WE(&Wire,  ADDR_T1);
MPU6500_WE mpuRPSIS = MPU6500_WE(&Wire1, ADDR_RPSIS);
bool imuT12OK = false, imuT1OK = false, imuRPSISok = false;

// ─── MAX17048 (fuel gauge) ───────────────────────────────────────────────────
Adafruit_MAX17048 maxlipo;
bool fuelGaugeOK = false;
const float BAT_V_MAX = 4.2;    // 100%
const float BAT_V_MIN = 3.0;    // 0%
const float BAT_UMBRAL_BAJO = 20.0;   // % → pasa a rojo
const float BAT_UMBRAL_ALTO = 25.0;   // % → vuelve a verde (histéresis)
bool bateriaBaja = false;

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
float refRPSIS_pitch = 0, refRPSIS_roll = 0;   // NUEVO: referencia pelvis

// ─── Evaluación deslizante ───────────────────────────────────────────────────
unsigned long tUltimaEvalT1 = 0, tUltimaEvalT12 = 0;

// ─── Sesión activa (solo para registro/app, no condiciona la vibración) ──────
enum EstadoSesion { SESION_IDLE, SESION_RUNNING, SESION_PAUSED };
EstadoSesion estadoSesion = SESION_IDLE;
unsigned long tInicioSesion  = 0;
unsigned long tFinSesion     = 0;
unsigned long tUltimoMuestreo = 0;
unsigned int  alertasHapticas = 0;
float minBuena = 0.0, minMala = 0.0;

// ─── Vibración ───────────────────────────────────────────────────────────────
bool vibrando = false;
unsigned long tFinVibra = 0;

// ─── SD y config ─────────────────────────────────────────────────────────────
bool    sdDisponible       = false;
String  cfgDeviceName      = "ALINA Dispositivo";
int     cfgHapticIntensity = 1000;   // INTENSIDAD háptica (en la práctica: ms de vibración)
String  cfgLastCalibAt     = "";

// ─── Botón pulsación larga ───────────────────────────────────────────────────
unsigned long tBotonPresionado = 0;
bool botonEstabaPresionado = false, accionLargaHecha = false;

// ═══ LOGGING CSV (temporal, solo para pruebas) ═══════════════════════════════
#define MODO_LOGGING 0        // 1 = graba CSV en la SD ; 0 = desactivado (borrable)
#if MODO_LOGGING
File   logFile;                                   // CSV de la sesión actual
bool   logActivo   = false;                       // true mientras graba
int    numSesionLog = 0;                          // número de sesión actual
unsigned long tInicioLog = 0, tUltimoLog = 0;     // t=0 y control de 2 Hz
int    logContadorFlush  = 0;                     // para flush periódico
bool   vibroT12Log = false, vibroT1Log = false;   // estado de vibración por nivel
const unsigned long LOG_PERIODO_MS = 500;             // 2 Hz (una fila cada 500ms)
const unsigned long LOG_MAX_MS     = 30UL*60*1000;   // corte automático a 30 min
#endif

// ─── Prototipos (evitan problemas de orden de declaración en Arduino) ────────
void guardarConfig();
void cargarConfig();
void guardarOffsetsHW();
bool cargarOffsetsHW();
void guardarCalibracionSD();
bool cargarCalibracionSD();
void borrarTodoSD();
void wsSend(String &msg);
void wsEnviarStatus();
void wsEnviarPostura(float t1p, float t1r, float t12p, float t12r);
void wsEnviarAlerta(const char* fuente);
void wsEnviarFinSesion();
void procesarComando(const String &msg);
void webSocketEvent(uint8_t num, WStype_t type, uint8_t *payload, size_t length);
float bateriaPorcentaje();
void actualizarLEDbateria();
void apagarMotores();
void dispararVibracion(uint8_t motores);
bool malaPosturaT1(float p, float r);
bool malaPosturaT12(float p, float r);
void procesarBoton(float t1p, float t1r, float t12p, float t12r);
void resetBuffer();
float propMala(bool* buf);

// =============================================================================
// SD: config.json (preferencias del usuario)
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
    cfgDeviceName      = doc["device_name"]      | "ALINA Dispositivo";
    cfgHapticIntensity = doc["haptic_intensity"] | 1000;
    cfgLastCalibAt     = doc["last_calib_at"]    | "";
  }
  f.close();
  Serial.println("Config cargada de SD.");
}

// =============================================================================
// SD: offsets HW — AHORA se guardan los VALORES NUMÉRICOS reales
// =============================================================================

void guardarOffsetsHW() {
  if (!sdDisponible) return;
  if (SD.exists("/offsets_hw.txt")) SD.remove("/offsets_hw.txt");
  File f = SD.open("/offsets_hw.txt", FILE_WRITE);
  if (!f) return;

  // Para cada IMU guardamos accOffset (x,y,z) y gyrOffset (x,y,z)
  xyzFloat aT12 = mpuT12.getAccOffsets(),  gT12 = mpuT12.getGyrOffsets();
  xyzFloat aT1  = mpuT1.getAccOffsets(),   gT1  = mpuT1.getGyrOffsets();
  xyzFloat aRP  = mpuRPSIS.getAccOffsets(),gRP  = mpuRPSIS.getGyrOffsets();

  f.println("# Offsets HW ALINA (valores reales)");
  f.printf("T12_acc=%.6f,%.6f,%.6f\n", aT12.x, aT12.y, aT12.z);
  f.printf("T12_gyr=%.6f,%.6f,%.6f\n", gT12.x, gT12.y, gT12.z);
  f.printf("T1_acc=%.6f,%.6f,%.6f\n",  aT1.x,  aT1.y,  aT1.z);
  f.printf("T1_gyr=%.6f,%.6f,%.6f\n",  gT1.x,  gT1.y,  gT1.z);
  f.printf("RP_acc=%.6f,%.6f,%.6f\n",  aRP.x,  aRP.y,  aRP.z);
  f.printf("RP_gyr=%.6f,%.6f,%.6f\n",  gRP.x,  gRP.y,  gRP.z);
  f.close();
  Serial.println("Offsets HW guardados (valores reales) en SD.");
}

// Lee "x,y,z" desde una String y lo carga en un xyzFloat
static bool parseXYZ(const String &val, xyzFloat &out) {
  int c1 = val.indexOf(',');
  int c2 = val.indexOf(',', c1 + 1);
  if (c1 < 0 || c2 < 0) return false;
  out.x = val.substring(0, c1).toFloat();
  out.y = val.substring(c1 + 1, c2).toFloat();
  out.z = val.substring(c2 + 1).toFloat();
  return true;
}

bool cargarOffsetsHW() {
  if (!sdDisponible || !SD.exists("/offsets_hw.txt")) return false;
  File f = SD.open("/offsets_hw.txt");
  if (!f) return false;

  xyzFloat aT12, gT12, aT1, gT1, aRP, gRP;
  bool okT12a=false, okT12g=false, okT1a=false, okT1g=false, okRPa=false, okRPg=false;

  while (f.available()) {
    String linea = f.readStringUntil('\n'); linea.trim();
    if (linea.startsWith("#") || linea.length() == 0) continue;
    int eq = linea.indexOf('=');
    if (eq < 0) continue;
    String key = linea.substring(0, eq);
    String val = linea.substring(eq + 1);
    if      (key == "T12_acc") okT12a = parseXYZ(val, aT12);
    else if (key == "T12_gyr") okT12g = parseXYZ(val, gT12);
    else if (key == "T1_acc")  okT1a  = parseXYZ(val, aT1);
    else if (key == "T1_gyr")  okT1g  = parseXYZ(val, gT1);
    else if (key == "RP_acc")  okRPa  = parseXYZ(val, aRP);
    else if (key == "RP_gyr")  okRPg  = parseXYZ(val, gRP);
  }
  f.close();

  if (!(okT12a && okT12g && okT1a && okT1g && okRPa && okRPg)) {
    Serial.println("Offsets HW incompletos en SD. Hay que recalcular.");
    return false;
  }

  // IMPORTANTE: setAccOffsets/setGyrOffsets deben aplicarse ANTES de
  // setSampleRateDivider/setAccRange/etc. (sobrescriben configuraciones).
  if (imuT12OK)   { mpuT12.setAccOffsets(aT12);   mpuT12.setGyrOffsets(gT12); }
  if (imuT1OK)    { mpuT1.setAccOffsets(aT1);     mpuT1.setGyrOffsets(gT1);  }
  if (imuRPSISok) { mpuRPSIS.setAccOffsets(aRP);  mpuRPSIS.setGyrOffsets(gRP); }
  Serial.println("Offsets HW cargados de SD (valores reales).");
  return true;
}

// =============================================================================
// SD: calibración postural por individuo (incluye RPSIS de referencia)
// =============================================================================

void guardarCalibracionSD() {
  if (!sdDisponible) return;
  if (SD.exists("/calibracion.txt")) SD.remove("/calibracion.txt");
  File f = SD.open("/calibracion.txt", FILE_WRITE);
  if (!f) return;
  f.println("# Calibracion postural ALINA");
  f.print("refT1_pitch=");    f.println(refT1_pitch, 2);
  f.print("refT1_roll=");     f.println(refT1_roll, 2);
  f.print("refT12_pitch=");   f.println(refT12_pitch, 2);
  f.print("refT12_roll=");    f.println(refT12_roll, 2);
  f.print("refRPSIS_pitch="); f.println(refRPSIS_pitch, 2);
  f.print("refRPSIS_roll=");  f.println(refRPSIS_roll, 2);
  f.close();
  cfgLastCalibAt = String(millis());
  guardarConfig();
  Serial.println("Calibracion postural guardada en SD.");
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
    if (key == "refT1_pitch")    refT1_pitch    = val;
    if (key == "refT1_roll")     refT1_roll     = val;
    if (key == "refT12_pitch")   refT12_pitch   = val;
    if (key == "refT12_roll")    refT12_roll    = val;
    if (key == "refRPSIS_pitch") refRPSIS_pitch = val;
    if (key == "refRPSIS_roll")  refRPSIS_roll  = val;
  }
  f.close();
  return true;
}

// Borra TODO de la SD (botón 20s)
void borrarTodoSD() {
  if (!sdDisponible) return;
  if (SD.exists("/offsets_hw.txt"))  SD.remove("/offsets_hw.txt");
  if (SD.exists("/calibracion.txt")) SD.remove("/calibracion.txt");
  if (SD.exists("/config.json"))     SD.remove("/config.json");
  Serial.println(">> microSD borrada por completo (offsets + calibracion + config).");
}

// =============================================================================
// WebSocket — enviar
// =============================================================================

void wsSend(String &msg) {
  if (wsClient >= 0) webSocket.sendTXT(wsClient, msg);
}

void wsEnviarStatus() {
  StaticJsonDocument<160> doc;
  doc["type"]       = "status";
  doc["calibrated"] = (estadoCalib == CALIBRADO);
  doc["imu_t1"]     = imuT1OK;
  doc["imu_t12"]    = imuT12OK;
  doc["imu_rpsis"]  = imuRPSISok;
  doc["battery"]    = (int)round(bateriaPorcentaje());  // 0-100, o -1 si no hay fuel gauge
  String out; serializeJson(doc, out); wsSend(out);
}

// RPSIS ya no se envía: es solo referencia interna.
void wsEnviarPostura(float t1p, float t1r, float t12p, float t12r) {
  StaticJsonDocument<160> doc;
  doc["type"]      = "posture";
  doc["t1_pitch"]  = t1p;   doc["t1_roll"]  = t1r;
  doc["t12_pitch"] = t12p;  doc["t12_roll"] = t12r;
  String out; serializeJson(doc, out); wsSend(out);
}

void wsEnviarAlerta(const char* fuente) {
  StaticJsonDocument<64> doc;
  doc["type"]   = "alert";
  doc["source"] = fuente;
  doc["count"]  = alertasHapticas;
  String out; serializeJson(doc, out); wsSend(out);
}

void wsEnviarFinSesion() {
  if (estadoSesion == SESION_IDLE) return;
  tFinSesion = millis();
  float durMin = (tFinSesion - tInicioSesion) / 60000.0;
  StaticJsonDocument<192> doc;
  doc["type"]             = "session_end";
  doc["started_at_ms"]    = tInicioSesion;
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
      tUltimoMuestreo = millis();
      StaticJsonDocument<32> ack;
      ack["type"]  = "session_status";
      ack["state"] = "running";
      String aout; serializeJson(ack, aout); wsSend(aout);
      Serial.println("Sesión reanudada.");
    }

  } else if (strcmp(cmd, "stop_session") == 0) {
    wsEnviarFinSesion();
    estadoSesion = SESION_IDLE;
    StaticJsonDocument<32> ack;
    ack["type"]  = "session_status";
    ack["state"] = "idle";
    String aout; serializeJson(ack, aout); wsSend(aout);

  } else if (strcmp(cmd, "calibrate") == 0) {
    // Calibración por app: mismo flujo de un solo toque que el botón físico.
    // Arranca la calibración y se autocompleta a los 5s (el timer en loop() la cierra).
    xyzFloat aT1 = mpuT1.getAngles(), aT12 = mpuT12.getAngles(), aRP = mpuRPSIS.getAngles();
    (void)aRP;
    procesarBoton(aT1.y, aT1.x, aT12.y, aT12.x);   // misma lógica que el botón

  } else if (strcmp(cmd, "set_config") == 0) {
    if (doc.containsKey("device_name"))       cfgDeviceName      = doc["device_name"].as<String>();
    if (doc.containsKey("haptic_intensity"))  cfgHapticIntensity = doc["haptic_intensity"];
    guardarConfig();
    Serial.println("Config actualizada desde la app.");

  } else if (strcmp(cmd, "test_vibration") == 0) {
    unsigned long durMs = doc["haptic_intensity"] | (unsigned long)VIBRA_MS;
    dispararVibracion(0x0F);
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
// Porcentaje por regla de tres: 4.2V=100%, 3.0V=0%. Ignora el cellPercent() del chip.
float bateriaPorcentaje() {
  if (!fuelGaugeOK) return -1.0;
  float v = maxlipo.cellVoltage();
  float pct = (v - BAT_V_MIN) / (BAT_V_MAX - BAT_V_MIN) * 100.0;
  if (pct > 100.0) pct = 100.0;
  if (pct < 0.0)   pct = 0.0;
  return pct;
}

void actualizarLEDbateria() {
  if (!fuelGaugeOK) {                 // sin sensor: verde fijo, no doy falsa alarma
    digitalWrite(LED_VERDE_PIN, HIGH);
    digitalWrite(LED_ROJO_PIN, LOW);
    return;
  }
  float pct = bateriaPorcentaje();
  // histéresis: baja a rojo si <20%, no vuelve a verde hasta >25%
  if (bateriaBaja && pct > BAT_UMBRAL_ALTO)       bateriaBaja = false;
  else if (!bateriaBaja && pct < BAT_UMBRAL_BAJO) bateriaBaja = true;

  digitalWrite(LED_ROJO_PIN,  bateriaBaja ? HIGH : LOW);
  digitalWrite(LED_VERDE_PIN, bateriaBaja ? LOW  : HIGH);
}

void apagarMotores() {
  gpio_set_level((gpio_num_t)M1_PIN, 0); gpio_set_level((gpio_num_t)M2_PIN, 0);
  gpio_set_level((gpio_num_t)M3_PIN, 0); gpio_set_level((gpio_num_t)M4_PIN, 0);
}

// Enciende motores según un bitmask: bit0=M1, bit1=M2, bit2=M3, bit3=M4
void dispararVibracion(uint8_t motores) {
  if (motores & 0x01) gpio_set_level((gpio_num_t)M1_PIN, 1);
  if (motores & 0x02) gpio_set_level((gpio_num_t)M2_PIN, 1);
  if (motores & 0x04) gpio_set_level((gpio_num_t)M3_PIN, 1);
  if (motores & 0x08) gpio_set_level((gpio_num_t)M4_PIN, 1);
  #if MODO_LOGGING
    if (motores & 0x03) vibroT12Log = true;   // M1 o M2 = T12
    if (motores & 0x0C) vibroT1Log  = true;   // M3 o M4 = T1
  #endif
  vibrando = true;
  unsigned long dur = (cfgHapticIntensity > 0) ? (unsigned long)cfgHapticIntensity : VIBRA_MS;
  tFinVibra = millis() + dur;
  alertasHapticas++;
}


// Clasificadores separados por condición (cada uno prende motores distintos)
bool malaPitchT1(float p)   { return (p < T1_PITCH_MIN); }       // → M3+M4
bool malaPitchT12(float p)  { return (p < T12_PITCH_MIN); }      // → M1+M2
bool malaRollT1Neg(float r) { return (r < -T1_ROLL_LIM); }       // → M3+M1
bool malaRollT1Pos(float r) { return (r >  T1_ROLL_LIM); }       // → M4+M2

// Helpers "postura mala en general" (para min_buena/min_mala del registro)
bool malaPosturaT1(float p, float r)  { return malaPitchT1(p) || malaRollT1Neg(r) || malaRollT1Pos(r); }
bool malaPosturaT12(float p, float r) { (void)r; return malaPitchT12(p); }


// =============================================================================
// Buffer deslizante
// =============================================================================

void resetBuffer() {
  bufIdx = 0; bufLlenado = 0;
  for (int i = 0; i < BUF_N; i++) {
    bufT12p[i] = false; bufT1p[i] = false;
    bufT1rNeg[i] = false; bufT1rPos[i] = false;
  }
}

// Proporción de "true" sobre las muestras válidas del buffer
float propMala(bool* buf) {
  if (bufLlenado == 0) return 0.0;
  int malas = 0;
  for (int i = 0; i < bufLlenado; i++) if (buf[i]) malas++;
  return (float)malas / bufLlenado;
}

// =============================================================================
// Calibración por botón (cero postural por individuo, RPSIS incluido)
// =============================================================================

// NUEVO FLUJO: un solo toque arranca la calibración. Se completa SOLA a los 5s
// (el buzzer suena "pi pi" durante esos 5s; ver el bloque de calibración en loop()).
// Los toques extra mientras calibra se ignoran.
void procesarBoton(float t1p, float t1r, float t12p, float t12r) {
  (void)t1p; (void)t1r; (void)t12p; (void)t12r;   // la referencia se captura en loop() al cumplirse los 5s
  if (estadoCalib == SIN_CALIBRAR || estadoCalib == CALIBRADO) {
    estadoCalib  = ESPERANDO_FIN;
    tInicioCalib = millis();
    if (sdDisponible && SD.exists("/calibracion.txt")) SD.remove("/calibracion.txt");
    Serial.println(">> Calibrando: mantené la postura 5s (el buzzer suena hasta terminar).");
  }
  // Si ya está en ESPERANDO_FIN, se ignora: la completa el timer en loop().
}


#if MODO_LOGGING
// Lee /contador.txt, lo incrementa y lo vuelve a guardar. Así los números nunca se repiten.
int siguienteNumeroSesion() {
  int n = 0;
  if (SD.exists("/contador.txt")) {
    File f = SD.open("/contador.txt");
    if (f) { n = f.parseInt(); f.close(); }
  }
  n++;
  if (SD.exists("/contador.txt")) SD.remove("/contador.txt");
  File f = SD.open("/contador.txt", FILE_WRITE);
  if (f) { f.print(n); f.close(); }
  return n;
}

// Cierra limpio el CSV abierto (si hay uno).
void cerrarLog() {
  if (!logActivo) return;
  logFile.flush();
  logFile.close();
  logActivo = false;
  Serial.println(">> CSV de sesion cerrado.");
}

// Cierra el anterior y abre un CSV nuevo numerado con la calibración en la cabecera.
void iniciarLog() {
  if (!sdDisponible) return;
  cerrarLog();
  numSesionLog = siguienteNumeroSesion();
  char nombre[20];
  snprintf(nombre, sizeof(nombre), "/S%03d.csv", numSesionLog);
  logFile = SD.open(nombre, FILE_WRITE);
  if (!logFile) { Serial.printf("ERROR: no pude crear %s\n", nombre); return; }
  logFile.printf("# sesion=%d\n", numSesionLog);
  logFile.printf("# calib: refT1_pitch=%.2f refT1_roll=%.2f refT12_pitch=%.2f refT12_roll=%.2f refRPSIS_pitch=%.2f refRPSIS_roll=%.2f\n",
                 refT1_pitch, refT1_roll, refT12_pitch, refT12_roll, refRPSIS_pitch, refRPSIS_roll);
  logFile.println("sesion,t_ms,t1_pitch,t1_roll,t12_pitch,t12_roll,rpsis_pitch,rpsis_roll,mala_T12,mala_T1,vibro_T12,vibro_T1");
  logFile.flush();
  logActivo  = true;
  tInicioLog = millis();
  tUltimoLog = 0;
  Serial.printf(">> Grabando %s\n", nombre);
}

// Escribe una fila a 2 Hz. Corta sola a los 30 min.
void registrarMuestra(float t1p,float t1r,float t12p,float t12r,
                      float rpp,float rpr,bool malaT12,bool malaT1) {
  if (!logActivo) return;
  unsigned long ahora = millis();
  if (ahora - tInicioLog >= LOG_MAX_MS) {
    Serial.println(">> 30 min cumplidos: cierro la sesion automaticamente.");
    cerrarLog();
    return;
  }
  if (ahora - tUltimoLog < LOG_PERIODO_MS) return;   // submuestreo a 2 Hz
  tUltimoLog = ahora;
  logFile.printf("%d,%lu,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%d,%d,%d,%d\n",
                 numSesionLog, ahora - tInicioLog,
                 t1p,t1r,t12p,t12r,rpp,rpr,
                 malaT12?1:0, malaT1?1:0, vibroT12Log?1:0, vibroT1Log?1:0);
  if (++logContadorFlush >= 4) { logFile.flush(); logContadorFlush = 0; }  // flush cada 2s
}
#endif

// =============================================================================
// SETUP
// =============================================================================

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("=== ALINA Firmware v2.1 ===");
  pinMode(LED_VERDE_PIN, OUTPUT);
  for (int i = 0; i < 6; i++) { digitalWrite(LED_VERDE_PIN, HIGH); delay(150); digitalWrite(LED_VERDE_PIN, LOW); delay(150); }

  // Motores
  for (int p : {M1_PIN, M2_PIN, M3_PIN, M4_PIN}) {
    gpio_reset_pin((gpio_num_t)p);
    gpio_set_direction((gpio_num_t)p, GPIO_MODE_OUTPUT);
  }
  apagarMotores();
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);

  // NUEVO: buzzer y LEDs de estado
  pinMode(BUZZER_PIN, OUTPUT);    digitalWrite(BUZZER_PIN, LOW);
  pinMode(LED_VERDE_PIN, OUTPUT); digitalWrite(LED_VERDE_PIN, LOW);  // verde arranca apagado; titila durante el boot
  pinMode(LED_ROJO_PIN, OUTPUT);  digitalWrite(LED_ROJO_PIN, LOW);   // rojo apagado (batería, pendiente)

  // Botón
  pinMode(BOTON_PIN, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(BOTON_PIN), onBoton, FALLING);

  pinMode(BOOT_BTN_PIN, INPUT_PULLUP);   // BOOT ya tiene pull-up físico, pero lo dejamos explícito

  // I2C
  Wire.begin(SDA_PIN, SCL_PIN);
  Wire1.begin(SDA_RPSIS, SCL_RPSIS);

  // MAX17048 (fuel gauge) — está en el bus Wire1 (GPIO 25/26)
  if (maxlipo.begin(&Wire1)) {
    fuelGaugeOK = true;
    Serial.println("MAX17048 OK.");
  } else {
    Serial.println("WARN: MAX17048 no responde.");
  }

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

  // ── Offsets HW ──
  // Si existen y son válidos en la SD, se RECARGAN (valores reales) y NO se recalcula.
  // Si no, se calculan una vez (quieto y plano 3s) y se guardan.
  if (sdDisponible && cargarOffsetsHW()) {
    Serial.println("Offsets HW recuperados de SD. No recalibro.");
  } else {
    Serial.println("Calculando offsets HW (dejá los sensores quietos y planos 3s)...");
    delay(3000);
    if (imuT12OK)   mpuT12.autoOffsets();
    if (imuT1OK)    mpuT1.autoOffsets();
    if (imuRPSISok) mpuRPSIS.autoOffsets();
    if (sdDisponible) guardarOffsetsHW();
  }

  // Settings MPU (DESPUÉS de aplicar offsets, porque setAccOffsets los sobrescribe)
  MPU6500_WE* todos[] = {&mpuT12, &mpuT1, &mpuRPSIS};
  for (int i = 0; i < 3; i++) {
    todos[i]->setSampleRateDivider(5);
    todos[i]->setAccRange(MPU6500_ACC_RANGE_2G);
    todos[i]->setGyrRange(MPU6500_GYRO_RANGE_250);
    todos[i]->enableGyrDLPF();
    todos[i]->setGyrDLPF(MPU6500_DLPF_6);
  }

  // Calibración postural por individuo
  if (sdDisponible && cargarCalibracionSD()) {
    estadoCalib = CALIBRADO;
    Serial.println("Calibración postural cargada de SD. Dispositivo listo.");
  } else {
    estadoCalib = SIN_CALIBRAR;
    Serial.println("Sin calibración por individuo. No clasifica hasta calibrar (botón).");
  }

  // WiFiManager — intenta conectar, pero NO bloquea si no hay red.
  // El dispositivo funciona offline igual (calibración, detección, vibración).
  // WiFiManager wm;
  // wm.setConfigPortalTimeout(20);
  // wm.setConnectTimeout(15);   // intenta 15s y se rinde, no se cuelga
  // if (wm.autoConnect("ALINA-Setup")) {
  //   Serial.print("WiFi OK. IP: ");
  //   Serial.println(WiFi.localIP());
  // } else {
  //   Serial.println("Sin WiFi. Sigo en modo OFFLINE (mide y vibra igual).");
  // }

  // WiFi — si hay red guardada, intenta 15s y sigue. Si no hay, arranca OFFLINE directo.
  // NUNCA abre portal en el arranque. El portal se abre solo con BOOT 5s.
  // WiFiManager wm;
  // wm.setEnableConfigPortal(false);   // no abre portal en el arranque
  // wm.setConnectTimeout(15);          // si hay red guardada, intenta 15s
  // if (wm.autoConnect("ALINA-Setup")) {
  //   Serial.print("WiFi OK (ONLINE). IP: ");
  //   Serial.println(WiFi.localIP());
  //   digitalWrite(LED_VERDE_PIN, HIGH);   // verde fijo = online
  // } else {
  //   Serial.println("Sin WiFi (OFFLINE). Mide y vibra igual.");
  //   for (int i = 0; i < 8; i++) {         // parpadeo 2s = arrancó offline
  //     digitalWrite(LED_VERDE_PIN, HIGH); delay(125);
  //     digitalWrite(LED_VERDE_PIN, LOW);  delay(125);
  //   }
  //   digitalWrite(LED_VERDE_PIN, HIGH);   // vuelve a quedar fijo
  // }

  WiFiManager wm;
  wm.setEnableConfigPortal(false);   // no abre portal en el arranque
  wm.setConnectTimeout(15);          // si hay red guardada, intenta 15s
  if (wm.autoConnect("ALINA-Setup")) {
    Serial.print("WiFi OK (ONLINE). IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("Sin WiFi (OFFLINE). Mide y vibra igual.");
  }
  // Nota: el titileo verde de "arrancando" lo hace la última línea del setup
  // (actualizarLEDbateria fija el estado final rojo/verde).


  // mDNS
  if (MDNS.begin("alina")) Serial.println("mDNS OK. alina.local");
  else                     Serial.println("WARN: mDNS no pudo iniciarse.");

  // WebSocket
  webSocket.begin();
  webSocket.onEvent(webSocketEvent);
  Serial.println("WebSocket en puerto 81.");

  // Timer de muestreo
  timerMuestreo = timerBegin(1000000);
  timerAttachInterrupt(timerMuestreo, &onTimer);
  timerAlarm(timerMuestreo, PERIODO_MS * 1000, true, 0);

  resetBuffer();
  tUltimaEvalT1 = tUltimaEvalT12 = millis();
  
  actualizarLEDbateria();   // fin del arranque: deja de titilar y fija rojo/verde según batería
  Serial.println("Sistema listo.");
}

// =============================================================================
// LOOP
// =============================================================================

void loop() {
  unsigned long ahora = millis();
  webSocket.loop();
  
  // Chequeo de batería cada 30s (no en cada vuelta, para no saturar el I2C)
  static unsigned long tUltimaBat = 0;
  if (ahora - tUltimaBat > 30000) {
    actualizarLEDbateria();
    tUltimaBat = ahora;
  }

  // Calibración en curso: LED onboard parpadea, buzzer suena "pi pi", y a los 5s
  // se captura la referencia, se guarda y termina sola (flujo de un solo toque).
  if (estadoCalib == ESPERANDO_FIN) {
    digitalWrite(LED_PIN, (millis() / 250) % 2);          // LED onboard parpadea
    unsigned long fase = (ahora - tInicioCalib) % 500;    // ciclo de 500ms
    digitalWrite(BUZZER_PIN, (fase < 100) ? HIGH : LOW);  // 100ms ON = "pi ... pi ..."

    if (ahora - tInicioCalib >= CALIB_MIN_MS) {           // pasaron los 5s
      xyzFloat aT1  = mpuT1.getAngles();
      xyzFloat aT12 = mpuT12.getAngles();
      xyzFloat aRP  = mpuRPSIS.getAngles();
      refT1_pitch  = aT1.y;  refT1_roll  = aT1.x;
      refT12_pitch = aT12.y; refT12_roll = aT12.x;
      refRPSIS_pitch = aRP.y; refRPSIS_roll = aRP.x;
      refT12_pitch = aT12.y; refT12_roll = aT12.x;
      refRPSIS_pitch = aRP.y; refRPSIS_roll = aRP.x;
      Serial.printf(">> BRUTOS -> T1 P:%.1f R:%.1f | T12 P:%.1f R:%.1f | RP P:%.1f R:%.1f\n",
                    aT1.y, aT1.x, aT12.y, aT12.x, aRP.y, aRP.x);
      estadoCalib = CALIBRADO;
      resetBuffer();
      guardarCalibracionSD();
      #if MODO_LOGGING
        estadoSesion = SESION_RUNNING;   // marca sesión activa sin depender de la app
        iniciarLog();                    // cierra el CSV anterior (si había) y abre uno nuevo
      #endif
      wsEnviarStatus();
      digitalWrite(LED_PIN, LOW);
      // Beep final de "listo": un pitido largo
      digitalWrite(BUZZER_PIN, HIGH); delay(400); digitalWrite(BUZZER_PIN, LOW);
      Serial.println(">> Calibración COMPLETA y guardada. Ya mide.");
    }
  } else {
    digitalWrite(LED_PIN, LOW);
    digitalWrite(BUZZER_PIN, LOW);
  }



  // ── 0) Pulsación larga del botón ─────────────────────────────────────────
  bool botonAhora = (digitalRead(BOTON_PIN) == LOW);
  if (botonAhora) {
    if (!botonEstabaPresionado) {
      tBotonPresionado = ahora;
      accionLargaHecha = false;
    } else if (!accionLargaHecha) {
      unsigned long dur = ahora - tBotonPresionado;
      if (dur >= HW_WIPE_MS) {
        Serial.println(">> Borrando TODA la microSD (20s)...");
        borrarTodoSD();
        accionLargaHecha = true;
        delay(500);
        ESP.restart();   // arranca limpio: recalculará offsets y pedirá calibración
      }
    }
  }
  botonEstabaPresionado = botonAhora;

  // ── BOOT (GPIO 0) mantenido 5s → reset WiFi + portal (espera bloqueado) ──────
  static unsigned long tBootPresionado = 0;
  static bool bootEstabaPresionado = false, accionBootHecha = false;
  bool bootAhora = (digitalRead(BOOT_BTN_PIN) == LOW);
  if (bootAhora) {
    if (!bootEstabaPresionado) {
      tBootPresionado = ahora;
      accionBootHecha = false;
    } else if (!accionBootHecha && (ahora - tBootPresionado >= 5000)) {
      accionBootHecha = true;
      Serial.println(">> BOOT 5s: reset WiFi. Abriendo portal ALINA-Setup...");
      apagarMotores();                       // cortar cualquier vibración
      digitalWrite(LED_VERDE_PIN, LOW);      // apago verde: señal de "estoy en config"
      WiFiManager wm;
      wm.resetSettings();                    // borra la red vieja
      wm.setConfigPortalTimeout(0);          // 0 = SIN timeout: espera hasta que VOS conectes
      // startConfigPortal BLOQUEA acá hasta que cargues una red o conectes
      if (wm.startConfigPortal("ALINA-Setup")) {
        Serial.print(">> WiFi configurado OK. IP: ");
        Serial.println(WiFi.localIP());
      } else {
        Serial.println(">> Portal cerrado. Reiniciando...");
      }
      delay(500);
      ESP.restart();   // reinicia limpio, ya con la red guardada
    }
  }
  bootEstabaPresionado = bootAhora;

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
#if MODO_LOGGING
    vibroT12Log = false; vibroT1Log = false;
#endif
  }

  // ── 3) Tick de muestreo (10 Hz) ──────────────────────────────────────────
  if (tickMuestreo) {
    tickMuestreo = false;
    xyzFloat aT1    = imuT1OK    ? mpuT1.getAngles()    : xyzFloat{0,0,0};
    xyzFloat aT12   = imuT12OK   ? mpuT12.getAngles()   : xyzFloat{0,0,0};
    xyzFloat aRPSIS = imuRPSISok ? mpuRPSIS.getAngles() : xyzFloat{0,0,0};

    // Desviación de la pelvis respecto de SU referencia (RPSIS = referencia)
    float rp_p = aRPSIS.y - refRPSIS_pitch;
    float rp_r = aRPSIS.x - refRPSIS_roll;

    // Ángulo de T1/T12 = (medido - su ref) - (desviación de la pelvis)
    float t1p  = (aT1.y  - refT1_pitch)  - rp_p;
    float t1r  = (aT1.x  - refT1_roll)   - rp_r;
    float t12p = (aT12.y - refT12_pitch) - rp_p;
    float t12r = (aT12.x - refT12_roll)  - rp_r;

    if (estadoCalib == CALIBRADO) {
      // Enviar postura al WebSocket (5 Hz) — sin RPSIS
      if (wsClient >= 0 && estadoSesion == SESION_RUNNING) {
        static unsigned long ultimoWS = 0;
        if (ahora - ultimoWS > 200) {
          wsEnviarPostura(t1p, t1r, t12p, t12r);
          ultimoWS = ahora;
        }
      }

      // Acumular min_buena / min_mala (solo durante sesión, para el registro)
      if (estadoSesion == SESION_RUNNING) {
        float dt = (ahora - tUltimoMuestreo) / 60000.0;
        tUltimoMuestreo = ahora;
        if (malaPosturaT1(t1p, t1r) || malaPosturaT12(t12p, t12r)) minMala  += dt;
        else                                                       minBuena += dt;
      }

      // Escribir en los 4 buffers deslizantes (uno por condición)
      bufT12p[bufIdx]   = malaPitchT12(t12p);
      bufT1p[bufIdx]    = malaPitchT1(t1p);
      bufT1rNeg[bufIdx] = malaRollT1Neg(t1r);
      bufT1rPos[bufIdx] = malaRollT1Pos(t1r);
      bufIdx = (bufIdx + 1) % BUF_N;
      if (bufLlenado < BUF_N) bufLlenado++;

      #if MODO_LOGGING
      registrarMuestra(t1p, t1r, t12p, t12r, rp_p, rp_r,
                       malaPosturaT12(t12p, t12r), malaPosturaT1(t1p, t1r));
      #endif

      // Debug serial (cada 500ms) — sin imprimir RPSIS
      static unsigned long ultimoPrint = 0;
      if (ahora - ultimoPrint > 500) {
        ultimoPrint = ahora;
        xyzFloat g = mpuT1.getGValues();
        Serial.printf("T1 P:%.1f R:%.1f | T12 P:%.1f R:%.1f\n", t1p, t1r, t12p, t12r);
      }
    }
  }

  // ── 4) Evaluación deslizante cada 15s sobre los últimos 30s ──────────────
  if (estadoCalib == CALIBRADO && (ahora - tUltimaEvalT12 >= EVAL_CADA_MS)) {
    int nT12p=0, nT1p=0, nRn=0, nRp=0;
    for (int i = 0; i < bufLlenado; i++) {
      if (bufT12p[i])   nT12p++;
      if (bufT1p[i])    nT1p++;
      if (bufT1rNeg[i]) nRn++;
      if (bufT1rPos[i]) nRp++;
    }
    float pT12p = (bufLlenado>0) ? (float)nT12p/bufLlenado : 0.0;
    float pT1p  = (bufLlenado>0) ? (float)nT1p /bufLlenado : 0.0;
    float pRn   = (bufLlenado>0) ? (float)nRn  /bufLlenado : 0.0;
    float pRp   = (bufLlenado>0) ? (float)nRp  /bufLlenado : 0.0;

    uint8_t motores = 0;
    if (pT12p > PROP_UMBRAL) motores |= 0x03;   // pitch T12 → M1+M2
    if (pT1p  > PROP_UMBRAL) motores |= 0x0C;   // pitch T1  → M3+M4
    if (pRn   > PROP_UMBRAL) motores |= 0x05;   // roll T1(-) → M3+M1
    if (pRp   > PROP_UMBRAL) motores |= 0x0A;   // roll T1(+) → M4+M2

    Serial.printf("[T12] ventana 30s: %d malas / %d total (%.0f%%) → %s\n",
                  nT12p, bufLlenado, 100.0 * pT12p,
                  (pT12p > PROP_UMBRAL) ? "VIBRA motores T12 (M1+M2)" : "ok, no vibra");
    Serial.printf("[T1 ] ventana 30s: %d malas / %d total (%.0f%%) → %s\n",
                  nT1p, bufLlenado, 100.0 * pT1p,
                  (pT1p > PROP_UMBRAL) ? "VIBRA motores T1 (M3+M4)" : "ok, no vibra");

    if (motores) {
      dispararVibracion(motores);
      if (motores & 0x03) wsEnviarAlerta("T12");
      if (motores & 0x0C) wsEnviarAlerta("T1");
    }
    tUltimaEvalT12 = ahora;
  }


  // ── 4) Evaluación deslizante cada 15s sobre los últimos 30s ──────────────
  // if (estadoCalib == CALIBRADO && (ahora - tUltimaEvalT12 >= EVAL_CADA_MS)) {
  //   int malas = 0; for (int i = 0; i < bufLlenado; i++) if (bufMalaT12[i]) malas++;
  //   float prop = (bufLlenado > 0) ? (float)malas / bufLlenado : 0.0;
  //   Serial.printf("[T12] ventana 30s: %d malas / %d total (%.0f%%) → %s\n",
  //                 malas, bufLlenado, 100.0 * prop,
  //                 (prop > PROP_UMBRAL) ? "VIBRA motores T12 (M1+M2)" : "ok, no vibra");
  //   if (prop > PROP_UMBRAL) { dispararVibracion(true, false); wsEnviarAlerta("T12"); }
  //   tUltimaEvalT12 = ahora;
  // }
  // if (estadoCalib == CALIBRADO && (ahora - tUltimaEvalT1 >= EVAL_CADA_MS)) {
  //   int malas = 0; for (int i = 0; i < bufLlenado; i++) if (bufMalaT1[i]) malas++;
  //   float prop = (bufLlenado > 0) ? (float)malas / bufLlenado : 0.0;
  //   Serial.printf("[T1 ] ventana 30s: %d malas / %d total (%.0f%%) → %s\n",
  //                 malas, bufLlenado, 100.0 * prop,
  //                 (prop > PROP_UMBRAL) ? "VIBRA motores T1 (M3+M4)" : "ok, no vibra");
  //   if (prop > PROP_UMBRAL) { dispararVibracion(false, true); wsEnviarAlerta("T1"); }
  //   tUltimaEvalT1 = ahora;
  // }

}
