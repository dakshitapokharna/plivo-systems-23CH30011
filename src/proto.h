// Wire formats and shared constants for the flaky-network sender/receiver.
//
// Two formats exist:
//   - Harness format (fixed by the assignment): 4-byte big-endian seq +
//     160-byte payload, used on the harness-facing legs (47010 in, 47020
//     out).
//   - Media format (ours to design): rides between our own sender and
//     receiver (47001/47002). It's the harness format for a "primary"
//     frame, optionally followed by a second harness-format-shaped block
//     carrying a redundant copy of an earlier frame. Datagram length alone
//     tells the receiver which shape it got (164 bytes = primary only, 328
//     = with redundancy) - no extra header byte needed.
#pragma once

#include <array>
#include <cstdint>
#include <cstring>

namespace proto {

constexpr int PAYLOAD_SIZE = 160;
constexpr int HARNESS_FRAME_SIZE = 4 + PAYLOAD_SIZE;         // 164
constexpr int MEDIA_PRIMARY_ONLY_SIZE = HARNESS_FRAME_SIZE;   // 164
constexpr int MEDIA_WITH_REDUNDANT_SIZE = 2 * HARNESS_FRAME_SIZE; // 328

constexpr int FRAME_INTERVAL_MS = 20;

constexpr const char* ADDR_LOOPBACK = "127.0.0.1";

// Fixed architecture ports (all UDP, all 127.0.0.1). Direction is which
// side of our pair owns the socket.
constexpr int PORT_HARNESS_SOURCE_TO_SENDER = 47010;   // sender listens
constexpr int PORT_SENDER_TO_RELAY = 47001;            // sender sends (relay listens)
constexpr int PORT_RELAY_TO_RECEIVER = 47002;          // receiver listens
constexpr int PORT_RECEIVER_TO_HARNESS_PLAYER = 47020; // receiver sends (harness player listens)
constexpr int PORT_RECEIVER_FEEDBACK_TO_RELAY = 47003; // optional feedback path, unused by this design
constexpr int PORT_RELAY_FEEDBACK_TO_SENDER = 47004;   // optional feedback path, unused by this design

// One 20ms unit of media: a sequence number and its payload.
struct Frame {
    uint32_t seq = 0;
    std::array<uint8_t, PAYLOAD_SIZE> payload{};
};

inline void put_u32be(uint8_t* buf, uint32_t v) {
    buf[0] = static_cast<uint8_t>(v >> 24);
    buf[1] = static_cast<uint8_t>(v >> 16);
    buf[2] = static_cast<uint8_t>(v >> 8);
    buf[3] = static_cast<uint8_t>(v);
}

inline uint32_t get_u32be(const uint8_t* buf) {
    return (static_cast<uint32_t>(buf[0]) << 24) | (static_cast<uint32_t>(buf[1]) << 16) |
           (static_cast<uint32_t>(buf[2]) << 8) | static_cast<uint32_t>(buf[3]);
}

// Matches the fixed harness wire format exactly.
inline void encode_harness_frame(uint8_t* out, uint32_t seq, const uint8_t* payload) {
    put_u32be(out, seq);
    std::memcpy(out + 4, payload, PAYLOAD_SIZE);
}

inline bool decode_harness_frame(const uint8_t* buf, int len, Frame& out) {
    if (len != HARNESS_FRAME_SIZE) return false;
    out.seq = get_u32be(buf);
    std::memcpy(out.payload.data(), buf + 4, PAYLOAD_SIZE);
    return true;
}

// What crosses the relay between our own sender and receiver.
struct MediaPacket {
    Frame primary;
    bool has_redundant = false;
    Frame redundant;
};

// Packs a primary frame and an optional redundant copy of an earlier frame
// into one datagram. Returns the encoded length. `out` must have room for
// MEDIA_WITH_REDUNDANT_SIZE bytes.
inline int encode_media(uint8_t* out, const Frame& primary, bool has_redundant, const Frame& redundant) {
    encode_harness_frame(out, primary.seq, primary.payload.data());
    if (!has_redundant) return MEDIA_PRIMARY_ONLY_SIZE;
    encode_harness_frame(out + HARNESS_FRAME_SIZE, redundant.seq, redundant.payload.data());
    return MEDIA_WITH_REDUNDANT_SIZE;
}

// Parses a datagram produced by encode_media. Length alone disambiguates
// the two shapes.
inline bool decode_media(const uint8_t* buf, int len, MediaPacket& out) {
    if (len == MEDIA_PRIMARY_ONLY_SIZE) {
        out.has_redundant = false;
        return decode_harness_frame(buf, len, out.primary);
    }
    if (len == MEDIA_WITH_REDUNDANT_SIZE) {
        if (!decode_harness_frame(buf, HARNESS_FRAME_SIZE, out.primary)) return false;
        if (!decode_harness_frame(buf + HARNESS_FRAME_SIZE, HARNESS_FRAME_SIZE, out.redundant)) return false;
        out.has_redundant = true;
        return true;
    }
    return false;
}

} // namespace proto
