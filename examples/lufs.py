"""Integrated LUFS (ITU-R BS.1770-4) of a wav file, numpy only."""
import sys, wave
import numpy as np


def biquad(x, b, a):
    y = np.zeros_like(x)
    x1 = x2 = y1 = y2 = 0.0
    b0, b1, b2 = b
    a1, a2 = a[1], a[2]
    for i in range(len(x)):
        y0 = b0*x[i] + b1*x1 + b2*x2 - a1*y1 - a2*y2
        x2, x1 = x1, x[i]
        y2, y1 = y1, y0
        y[i] = y0
    return y


def k_weight(x, sr):
    # stage 1: high-shelf (BS.1770-4 pre-filter)
    f0, G, Q = 1681.9744509555319, 3.99984385397, 0.7071752369554193
    K = np.tan(np.pi*f0/sr); Vh = 10**(G/20); Vb = Vh**0.4996667741545416
    a0 = 1 + K/Q + K*K
    b = [(Vh + Vb*K/Q + K*K)/a0, 2*(K*K - Vh)/a0, (Vh - Vb*K/Q + K*K)/a0]
    a = [1.0, 2*(K*K - 1)/a0, (1 - K/Q + K*K)/a0]
    x = biquad(x, b, a)
    # stage 2: RLB high-pass
    f0, Q = 38.13547087602444, 0.5003270373238773
    K = np.tan(np.pi*f0/sr)
    a0 = 1 + K/Q + K*K
    b = [1/a0, -2/a0, 1/a0]
    a = [1.0, 2*(K*K - 1)/a0, (1 - K/Q + K*K)/a0]
    return biquad(x, b, a)


def integrated_lufs(path):
    w = wave.open(path); p = w.getparams()
    x = np.frombuffer(w.readframes(p.nframes), dtype=np.int16).astype(np.float64)/32768
    chans = [k_weight(x[c::p.nchannels], p.framerate) for c in range(p.nchannels)]
    sr = p.framerate
    blk, hop = int(0.4*sr), int(0.1*sr)
    n = (len(chans[0]) - blk)//hop
    z = np.array([sum(np.mean(c[i*hop:i*hop+blk]**2) for c in chans) for i in range(n)])
    lk = -0.691 + 10*np.log10(z + 1e-12)
    gated = z[lk > -70]                                  # absolute gate
    rel = -0.691 + 10*np.log10(gated.mean()) - 10        # relative gate
    final = z[(lk > -70) & (lk > rel + 0.691 - 0.691)]
    final = gated[(-0.691 + 10*np.log10(gated + 1e-12)) > rel]
    return -0.691 + 10*np.log10(final.mean())


if __name__ == "__main__":
    print(f"{integrated_lufs(sys.argv[1]):.1f} LUFS integrated")
