/* 
 *  LDR pulse counter for electricity meters having a pulse-led
 *  Works with generic ESP8266-wifi module
 *  
 *  Strongly influenced by https://randomnerdtutorials.com/esp8266-nodemcu-mqtt-publish-bme680-arduino/
 *  
 *  Report issues against https://github.com/mtaponen/home_automation_stuff
 *  Feel free to use
 *  Marko Taponen
 */

#include <ESP8266WiFi.h>
#include <Ticker.h>
#include <AsyncMqttClient.h>

#define WIFI_SSID "YOUR_SSID_HERE"
#define WIFI_PASSWORD "YOUR_WIFI_PASS"

#define MQTT_HOST IPAddress(192, 168, XXX, XXX)
// For a cloud MQTT broker, type the domain name
//#define MQTT_HOST "example.com"
#define MQTT_PORT 1883

#define MQTT_PUB_ENERGY "esp/ldr/energy"

// 1Mohm LDR between +5V to A0
// Downpull - 10kohm resistor from A0 to GND
const int LDR = A0;

// Wemos onboard LED will be constantly LOW = on when connected, 
// when blink is detected led is turned off
const int LED = 2; //GPIO2 = D4
// Treshold when we see light
const int TRESHOLD = 500;
// Debounce - how many loops until it is deemed real
const int DEBOUNCE_LIMIT = 3;
// MQTT Send Interval
const int SEND_EVERY_MILLIS = 10 * 1000;



int input_val = 0;
int pulse_counter = 0;
int loop_counter = 0;
int last_send_millis = 0;

AsyncMqttClient mqttClient;
Ticker mqttReconnectTimer;

WiFiEventHandler wifiConnectHandler;
WiFiEventHandler wifiDisconnectHandler;
Ticker wifiReconnectTimer;

void connectToWifi() {
  Serial.println("Connecting to Wi-Fi...");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
}

void connectToMqtt() {
  Serial.println("Connecting to MQTT...");
  mqttClient.connect();
}

void onWifiConnect(const WiFiEventStationModeGotIP& event) {
  Serial.println("Connected to Wi-Fi.");
  connectToMqtt();
}

void onWifiDisconnect(const WiFiEventStationModeDisconnected& event) {
  Serial.println("Disconnected from Wi-Fi.");
  mqttReconnectTimer.detach(); // ensure we don't reconnect to MQTT while reconnecting to Wi-Fi
  wifiReconnectTimer.once_ms(100, connectToWifi);
}

void onMqttConnect(bool sessionPresent) {
  Serial.println("Connected to MQTT.");
  Serial.print("Session present: ");
  Serial.println(sessionPresent);
  digitalWrite(LED, LOW);
}

void onMqttDisconnect(AsyncMqttClientDisconnectReason reason) {
  String text; 
    switch( reason) {
    case AsyncMqttClientDisconnectReason::TCP_DISCONNECTED:
       text = "TCP_DISCONNECTED"; 
       break; 
    case AsyncMqttClientDisconnectReason::MQTT_UNACCEPTABLE_PROTOCOL_VERSION:
       text = "MQTT_UNACCEPTABLE_PROTOCOL_VERSION"; 
       break; 
    case AsyncMqttClientDisconnectReason::MQTT_IDENTIFIER_REJECTED:
       text = "MQTT_IDENTIFIER_REJECTED";  
       break;
    case AsyncMqttClientDisconnectReason::MQTT_SERVER_UNAVAILABLE: 
       text = "MQTT_SERVER_UNAVAILABLE"; 
       break;
    case AsyncMqttClientDisconnectReason::MQTT_MALFORMED_CREDENTIALS:
       text = "MQTT_MALFORMED_CREDENTIALS"; 
       break;
    case AsyncMqttClientDisconnectReason::MQTT_NOT_AUTHORIZED:
       text = "MQTT_NOT_AUTHORIZED"; 
       break;
    
    }
  Serial.printf("Disconnected from the broker reason = %s\n", text.c_str() );
  digitalWrite(LED, HIGH);
  if (WiFi.isConnected()) {
    mqttReconnectTimer.once_ms(500, connectToMqtt);
  }
}

void onMqttSubscribe(uint16_t packetId, uint8_t qos) {
  Serial.println("Subscribe acknowledged.");
  Serial.print("  packetId: ");
  Serial.println(packetId);
  Serial.print("  qos: ");
  Serial.println(qos);
}

void onMqttUnsubscribe(uint16_t packetId) {
  Serial.println("Unsubscribe acknowledged.");
  Serial.print("  packetId: ");
  Serial.println(packetId);
}

void onMqttMessage(char* topic, char* payload, AsyncMqttClientMessageProperties properties, size_t len, size_t index, size_t total) {
  Serial.println("Publish received.");
  Serial.print("  topic: ");
  Serial.println(topic);
  Serial.print("  qos: ");
  Serial.println(properties.qos);
  Serial.print("  dup: ");
  Serial.println(properties.dup);
  Serial.print("  retain: ");
  Serial.println(properties.retain);
  Serial.print("  len: ");
  Serial.println(len);
  Serial.print("  index: ");
  Serial.println(index);
  Serial.print("  total: ");
  Serial.println(total);
}

void onMqttPublish(uint16_t packetId) {
  Serial.println("Publish acknowledged.");
  Serial.print("  packetId: ");
  Serial.println(packetId);
}

void setup() {
  Serial.begin(115200);
  Serial.println();
  Serial.println();
  Serial.println("Boot ok");
  pinMode(LED, OUTPUT);
  digitalWrite(LED, HIGH);
  
  last_send_millis = millis();

  wifiConnectHandler = WiFi.onStationModeGotIP(onWifiConnect);
  wifiDisconnectHandler = WiFi.onStationModeDisconnected(onWifiDisconnect);
  WiFi.setSleepMode(WIFI_NONE_SLEEP);

  mqttClient.onConnect(onMqttConnect);
  mqttClient.onDisconnect(onMqttDisconnect);
  mqttClient.onSubscribe(onMqttSubscribe);
  mqttClient.onUnsubscribe(onMqttUnsubscribe);
  mqttClient.onMessage(onMqttMessage);
  mqttClient.onPublish(onMqttPublish);
  mqttClient.setClientId("Energy");
  mqttClient.setCredentials("energy", "energy");
  
  mqttClient.setServer(MQTT_HOST, MQTT_PORT);
  mqttClient.setKeepAlive(60); // 60s

  connectToWifi();
}

void loop() {
  // Read LDR Value
  // If over treshold turn off the LED & increase loopcounter
  // Otherwise check 
  //   if counter is big enough (debounce) we have a pulse
  //   turn on the LED
  input_val = analogRead(LDR); 
  if (input_val > TRESHOLD) {
    loop_counter = loop_counter + 1;
    digitalWrite(LED, HIGH);
  } else if (loop_counter > 0) {
    if (loop_counter > DEBOUNCE_LIMIT) {
      pulse_counter = pulse_counter + 1;
    }
    //Serial.print("loop: ");
    Serial.println(loop_counter);
    loop_counter = 0;
    digitalWrite(LED, LOW);
  }

  // Check if enough time since last send and send if needed & reset the pulse counter 
  // So the message is "x pulses since last message"
  if (millis() - last_send_millis > SEND_EVERY_MILLIS) {
    last_send_millis = millis();
    Serial.print("Pulse_counter: ");
    Serial.println(pulse_counter);
    // Publish an MQTT message 
    if (mqttClient.connected()) {
      uint16_t packetIdPub1 = mqttClient.publish(MQTT_PUB_ENERGY, 1, true, String(pulse_counter).c_str());
      Serial.printf("Publishing on topic %s at QoS 1, packetId: %i\n", MQTT_PUB_ENERGY, packetIdPub1);
    }
    pulse_counter = 0;
  }

  // Take a nap and if mqtt-connection is down, turn off the led
  delay(5); // Needed so that the Wifi gets some runtime as well...
  if (!mqttClient.connected()){
    digitalWrite(LED, HIGH);
  }
  
}
