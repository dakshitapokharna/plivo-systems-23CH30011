// Reads media packets from the relay on port 47002 and forwards
// reconstructed frames to the harness player on port 47020 in the fixed
// harness format. Every frame we learn about - whether from its primary
// transmission or a redundant copy riding a later packet - is forwarded to
// the player the first time we see it, then never again. This keeps the
// receiver a single read loop with no playout timer: waiting doesn't help
// (early delivery isn't penalized) and holding frames back would only add
// delay for no benefit.
//
// A ring buffer keyed by seq (not arrival order) absorbs reordering; a
// per-slot "forwarded" flag absorbs duplicates and redundant copies of
// frames we already delivered.
#include "env.h"
#include "platform.h"
#include "proto.h"

#include <chrono>
#include <cstdio>
#include <vector>

namespace {

constexpr int RING_SIZE = 1024; // ~20s of lookback at 20ms/frame - comfortably more than any jitter window

struct Slot {
    uint32_t seq = 0;
    bool set = false;
    bool forwarded = false;
    std::array<uint8_t, proto::PAYLOAD_SIZE> payload{};
};

double now_epoch() {
    return std::chrono::duration<double>(std::chrono::system_clock::now().time_since_epoch()).count();
}

} // namespace

int main() {
    platform_socket_init();

    proto::Env env;
    try {
        env = proto::load_env();
    } catch (const std::exception& e) {
        std::fprintf(stderr, "receiver: env: %s\n", e.what());
        return 1;
    }

    socket_t in_sock;
    if (!make_udp_socket(in_sock) || !bind_udp(in_sock, proto::ADDR_LOOPBACK, proto::PORT_RELAY_TO_RECEIVER)) {
        std::fprintf(stderr, "receiver: listen 47002 failed\n");
        return 1;
    }
    set_recv_timeout_ms(in_sock, 500);

    socket_t out_sock;
    if (!make_udp_socket(out_sock)) {
        std::fprintf(stderr, "receiver: socket() for player failed\n");
        return 1;
    }
    struct sockaddr_in player_addr = make_addr(proto::ADDR_LOOPBACK, proto::PORT_RECEIVER_TO_HARNESS_PLAYER);

    std::vector<Slot> ring(RING_SIZE);
    double end_time = env.end_time_epoch();

    auto deliver = [&](const proto::Frame& f) {
        Slot& s = ring[f.seq % RING_SIZE];
        if (!s.set || s.seq != f.seq) {
            s = Slot{f.seq, true, false, f.payload};
        }
        if (!s.forwarded) {
            uint8_t out_buf[proto::HARNESS_FRAME_SIZE];
            proto::encode_harness_frame(out_buf, f.seq, f.payload.data());
            sendto(out_sock, reinterpret_cast<const char*>(out_buf), sizeof(out_buf), 0,
                   reinterpret_cast<struct sockaddr*>(&player_addr), sizeof(player_addr));
            s.forwarded = true;
        }
    };

    uint8_t buf[2048];
    for (;;) {
        int n = static_cast<int>(recvfrom(in_sock, reinterpret_cast<char*>(buf), sizeof(buf), 0, nullptr, nullptr));
        if (n < 0) {
            if (now_epoch() > end_time) break;
            continue;
        }

        proto::MediaPacket mp;
        if (!proto::decode_media(buf, n, mp)) continue;

        deliver(mp.primary);
        if (mp.has_redundant) deliver(mp.redundant);
    }

    CLOSESOCK(in_sock);
    CLOSESOCK(out_sock);
    platform_socket_cleanup();
    return 0;
}
