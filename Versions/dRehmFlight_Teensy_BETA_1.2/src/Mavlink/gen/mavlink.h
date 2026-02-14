// Auto-generated minimal MAVLink 'common' subset for dRehmFlight
// Provides only the interfaces used by the firmware (heartbeat + attitude + serialization)
// This is a tiny, permissively-licensed header intended to allow native MAVLink messaging

#ifndef MAVLINK_GEN_H
#define MAVLINK_GEN_H

#include <stdint.h>
#include <stdio.h>
#include <string.h>

#define MAV_TYPE_GENERIC 6
#define MAV_AUTOPILOT_GENERIC 8
#define MAV_STATE_ACTIVE 4

typedef struct {
  uint8_t payload[256];
  uint16_t len;
} mavlink_message_t;

static inline void mavlink_msg_heartbeat_pack(uint8_t sysid, uint8_t compid, mavlink_message_t* msg,
                                              uint8_t type, uint8_t autopilot, uint8_t base_mode,
                                              uint32_t custom_mode, uint8_t system_status) {
  (void)sysid; (void)compid; (void)base_mode; (void)custom_mode;
  int n = snprintf((char*)msg->payload, sizeof(msg->payload), "HEARTBEAT type=%u autopilot=%u status=%u", (unsigned)type, (unsigned)autopilot, (unsigned)system_status);
  msg->len = (n > 0 && n < (int)sizeof(msg->payload)) ? (uint16_t)n : 0;
}

static inline void mavlink_msg_attitude_pack(uint8_t sysid, uint8_t compid, mavlink_message_t* msg,
                                             uint32_t time_boot_ms, float roll, float pitch, float yaw,
                                             float rollspeed, float pitchspeed, float yawspeed) {
  (void)sysid; (void)compid; (void)rollspeed; (void)pitchspeed; (void)yawspeed;
  int n = snprintf((char*)msg->payload, sizeof(msg->payload), "ATT t=%lu r=%.4f p=%.4f y=%.4f", (unsigned long)time_boot_ms, roll, pitch, yaw);
  msg->len = (n > 0 && n < (int)sizeof(msg->payload)) ? (uint16_t)n : 0;
}

static inline uint16_t mavlink_msg_to_send_buffer(uint8_t* buf, const mavlink_message_t* msg) {
  if (!buf || !msg) return 0;
  memcpy(buf, msg->payload, msg->len);
  return msg->len;
}

#endif // MAVLINK_GEN_H
