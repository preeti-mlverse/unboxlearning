"""Write a tiny valid .glb (a coloured box on a plinth) for testing the 3D pipeline without external assets."""
import json
import struct
import sys

import numpy as np


def box(cx, cy, cz, sx, sy, sz):
    faces = [((1, 0, 0), [(1, -1, -1), (1, 1, -1), (1, 1, 1), (1, -1, 1)]),
             ((-1, 0, 0), [(-1, -1, 1), (-1, 1, 1), (-1, 1, -1), (-1, -1, -1)]),
             ((0, 1, 0), [(-1, 1, -1), (-1, 1, 1), (1, 1, 1), (1, 1, -1)]),
             ((0, -1, 0), [(-1, -1, 1), (-1, -1, -1), (1, -1, -1), (1, -1, 1)]),
             ((0, 0, 1), [(-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)]),
             ((0, 0, -1), [(1, -1, -1), (-1, -1, -1), (-1, 1, -1), (1, 1, -1)])]
    pos, nor, idx = [], [], []
    for n, quad in faces:
        base = len(pos)
        for x, y, z in quad:
            pos.append((cx + x * sx, cy + y * sy, cz + z * sz))
            nor.append(n)
        idx += [base, base + 1, base + 2, base, base + 2, base + 3]
    return pos, nor, idx


def write_glb(path):
    parts = [box(0, 0.6, 0, 0.5, 0.5, 0.5), box(0, 0.05, 0, 0.9, 0.05, 0.9)]
    colors = [[0.30, 0.25, 0.88, 1], [0.8, 0.8, 0.84, 1]]
    bin_ = b""
    views, accessors, meshes, nodes = [], [], [], []
    for i, (pos, nor, idx) in enumerate(parts):
        p = np.array(pos, np.float32).tobytes()
        n = np.array(nor, np.float32).tobytes()
        ix = np.array(idx, np.uint16).tobytes()
        for data, target in ((p, 34962), (n, 34962), (ix, 34963)):
            while len(bin_) % 4:
                bin_ += b"\0"
            views.append({"buffer": 0, "byteOffset": len(bin_), "byteLength": len(data), "target": target})
            bin_ += data
        v = len(views)
        pa = np.array(pos, np.float32)
        accessors += [
            {"bufferView": v - 3, "componentType": 5126, "count": len(pos), "type": "VEC3",
             "min": pa.min(0).tolist(), "max": pa.max(0).tolist()},
            {"bufferView": v - 2, "componentType": 5126, "count": len(nor), "type": "VEC3"},
            {"bufferView": v - 1, "componentType": 5123, "count": len(idx), "type": "SCALAR"}]
        a = len(accessors)
        meshes.append({"name": f"part{i}", "primitives": [
            {"attributes": {"POSITION": a - 3, "NORMAL": a - 2}, "indices": a - 1, "material": i}]})
        nodes.append({"mesh": i, "name": f"part{i}"})
    while len(bin_) % 4:
        bin_ += b"\0"
    gltf = {"asset": {"version": "2.0", "generator": "UnboxEd test"}, "scene": 0,
            "scenes": [{"nodes": list(range(len(nodes)))}], "nodes": nodes, "meshes": meshes,
            "materials": [{"pbrMetallicRoughness": {"baseColorFactor": c, "metallicFactor": 0.1, "roughnessFactor": 0.6}}
                          for c in colors],
            "accessors": accessors, "bufferViews": views, "buffers": [{"byteLength": len(bin_)}]}
    js = json.dumps(gltf).encode()
    js += b" " * ((4 - len(js) % 4) % 4)
    out = struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(bin_))
    out += struct.pack("<II", len(js), 0x4E4F534A) + js + struct.pack("<II", len(bin_), 0x004E4942) + bin_
    open(path, "wb").write(out)


if __name__ == "__main__":
    write_glb(sys.argv[1] if len(sys.argv) > 1 else "test_model.glb")
