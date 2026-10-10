"""Backend Pro Max — procedural 3D brand objects.
Usage: python scene.py <shot> <out.png> [res=900] [samples=16]
Shots: drawer  (card-catalog drawer — "every row sourced")
       cube    (glass cube holding a lit node — "MCP server")
       keycap  (ink ceramic keycap with a green prompt caret — "install")
Renders transparent PNG with a shadow-catcher floor (Cycles CPU, AgX)."""
import bpy, bmesh, sys, math, random
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
SHOT = argv[0] if argv else "drawer"
OUT = argv[1] if len(argv) > 1 else f"/tmp/{SHOT}.png"
RES = int(argv[2]) if len(argv) > 2 else 900
SAMPLES = int(argv[3]) if len(argv) > 3 else 16
SAVE_BLEND = argv[4] if len(argv) > 4 else None
random.seed(7)

PAPER = (0.953, 0.941, 0.910)
def srgb(h):
    h = h.lstrip("#"); c = [int(h[i:i+2], 16) / 255 for i in (0, 2, 4)]
    return tuple((x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4) for x in c) + (1,)
DOMAIN = ["#22D67A", "#5B9CF6", "#A78BFA", "#22D4E0", "#F2C14A", "#EE6A4E", "#FB8C3E", "#34D399", "#60A5FA", "#C084FC", "#FBBF24"]

# ── reset ────────────────────────────────────────────────────────────
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = SAMPLES
sc.cycles.use_denoising = True; sc.render.film_transparent = True
sc.render.resolution_x = sc.render.resolution_y = RES
try: sc.view_settings.view_transform = "AgX"; sc.view_settings.look = "AgX - Medium High Contrast"
except Exception: sc.view_settings.look = "Medium High Contrast"
world = bpy.data.worlds.new("W"); sc.world = world; world.use_nodes = True
bg = world.node_tree.nodes["Background"]; bg.inputs[0].default_value = srgb("#F3F0E8"); bg.inputs[1].default_value = 0.3

# ── material helpers ─────────────────────────────────────────────────
def principled(name, color, rough=0.5, metal=0.0, coat=0.0, emit=None, emit_s=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = color if len(color) == 4 else color + (1,)
    p.inputs["Roughness"].default_value = rough; p.inputs["Metallic"].default_value = metal
    if coat: p.inputs["Coat Weight"].default_value = coat
    if emit: p.inputs["Emission Color"].default_value = emit; p.inputs["Emission Strength"].default_value = emit_s
    return m

def bumpy(m, scale=40, strength=0.08, kind="noise"):
    nt = m.node_tree; p = nt.nodes["Principled BSDF"]
    tex = nt.nodes.new("ShaderNodeTexNoise" if kind == "noise" else "ShaderNodeTexVoronoi")
    tex.inputs["Scale"].default_value = scale
    b = nt.nodes.new("ShaderNodeBump"); b.inputs["Strength"].default_value = strength
    nt.links.new(tex.outputs[0 if kind == "noise" else "Distance"], b.inputs["Height"])
    nt.links.new(b.outputs["Normal"], p.inputs["Normal"]); return m

def wood(name):
    m = principled(name, srgb("#8A5A34"), rough=0.45, coat=0.4); nt = m.node_tree; p = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (1, 1, 14)
    n = nt.nodes.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = 3; n.inputs["Detail"].default_value = 8; n.inputs["Distortion"].default_value = 2.5
    cr = nt.nodes.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].color = srgb("#5E3A1E"); cr.color_ramp.elements[1].color = srgb("#B07A49")
    nt.links.new(tc.outputs["Object"], mp.inputs[0]); nt.links.new(mp.outputs[0], n.inputs[0])
    nt.links.new(n.outputs["Fac"], cr.inputs[0]); nt.links.new(cr.outputs[0], p.inputs["Base Color"]); return m

def glass(name, tint=(1, 1, 1, 1), gloss_rough=0.03, fres_blend=0.35):
    """Mix(Transparent, Glossy) by Layer Weight Fresnel — reads as glass, never renders black."""
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_MATERIAL": nt.nodes.remove(n)
    out = [n for n in nt.nodes if n.type == "OUTPUT_MATERIAL"][0]
    tr = nt.nodes.new("ShaderNodeBsdfTransparent"); tr.inputs[0].default_value = tint
    gl = nt.nodes.new("ShaderNodeBsdfGlossy"); gl.inputs["Roughness"].default_value = gloss_rough
    lw = nt.nodes.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = fres_blend
    mx = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(lw.outputs["Fresnel"], mx.inputs[0]); nt.links.new(tr.outputs[0], mx.inputs[1])
    nt.links.new(gl.outputs[0], mx.inputs[2]); nt.links.new(mx.outputs[0], out.inputs["Surface"])
    return m

def assign(o, m): o.data.materials.clear(); o.data.materials.append(m); return o

def box(name, size, loc, mat=None, bevel=0.0, segs=4):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc); o = bpy.context.object; o.name = name
    o.scale = size; bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        b = o.modifiers.new("bev", "BEVEL"); b.width = bevel; b.segments = segs; b.limit_method = "ANGLE"
    bpy.ops.object.shade_smooth()
    if mat: assign(o, mat)
    return o

def sphere(name, r, loc, mat, segs=48):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=segs, ring_count=segs // 2)
    o = bpy.context.object; o.name = name; bpy.ops.object.shade_smooth(); return assign(o, mat)

def lathe(name, profile, mat, steps=96, subsurf=2):
    """Spin a 2D (r, z) profile around Z with bmesh.ops.spin."""
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    vs = [bm.verts.new((r, 0, z)) for r, z in profile]
    for a, b in zip(vs, vs[1:]): bm.edges.new((a, b))
    bmesh.ops.spin(bm, geom=bm.verts[:] + bm.edges[:], cent=(0, 0, 0), axis=(0, 0, 1), angle=math.tau, steps=steps, use_merge=True)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    bm.to_mesh(me); bm.free(); o = bpy.data.objects.new(name, me); sc.collection.objects.link(o)
    if subsurf: o.modifiers.new("ss", "SUBSURF").levels = subsurf
    for p in o.data.polygons: p.use_smooth = True
    return assign(o, mat)

def floor():
    bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, 0)); f = bpy.context.object
    f.is_shadow_catcher = True; return f

def area(name, energy, loc, size, color=(1, 1, 1)):
    l = bpy.data.lights.new(name, "AREA"); l.energy = energy; l.size = size; l.color = color
    o = bpy.data.objects.new(name, l); o.location = loc; sc.collection.objects.link(o)
    d = Vector((0, 0, 0.6)) - Vector(loc); o.rotation_euler = d.to_track_quat("-Z", "Y").to_euler(); return o

def camera(loc, look, lens=55):
    c = bpy.data.cameras.new("Cam"); c.lens = lens; o = bpy.data.objects.new("Cam", c); sc.collection.objects.link(o)
    o.location = loc; o.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat("-Z", "Y").to_euler(); sc.camera = o

def std_lights(k=500, f=120, r=260):
    area("Key", k, (4, -4, 6), 4); area("Fill", f, (-5, -2, 3), 6, (0.95, 0.97, 1)); area("Rim", r, (-1, 5, 4), 3, (0.9, 1, 0.94))

# ── shots ────────────────────────────────────────────────────────────
def shot_drawer():
    W = wood("Wood"); card = bumpy(principled("Card", srgb("#F7F3E8"), rough=0.75), 120, 0.03)
    brass = principled("Brass", srgb("#C49A4A"), rough=0.28, metal=1.0)
    L, D, H, t = 3.2, 1.6, 0.9, 0.08   # drawer interior-ish dims
    box("Bottom", (L, D, t), (0, 0, t / 2), W, 0.01)
    box("Front", (t * 1.6, D + 0.16, H + 0.12), (L / 2 + t * 0.8, 0, (H + 0.12) / 2), W, 0.02)
    box("Back", (t, D, H * 0.9), (-L / 2 + t / 2, 0, H * 0.45), W, 0.01)
    for s in (-1, 1): box(f"Side{s}", (L, t, H * 0.8), (0, s * (D / 2 - t / 2), H * 0.4), W, 0.01)
    # brass label holder + pull on the front face
    box("Label", (0.02, 0.62, 0.3), (L / 2 + t * 1.6 + 0.01, 0, H * 0.68), brass, 0.01)
    box("LabelCard", (0.01, 0.52, 0.2), (L / 2 + t * 1.6 + 0.02, 0, H * 0.68), card)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.17, minor_radius=0.03, location=(L / 2 + t * 1.6 + 0.04, 0, H * 0.32), rotation=(0, math.pi / 2, 0))
    bpy.ops.object.shade_smooth(); assign(bpy.context.object, brass)
    # index cards standing, leaning slightly, each with a coloured domain tab
    n = 26; x0 = -L / 2 + 0.22
    for i in range(n):
        x = x0 + i * (L - 0.5) / n; lean = math.radians(-9 + random.uniform(-2, 2))
        hi = 0.58 if i == 17 else 0.0
        cz = H * 0.95 / 2 + t + hi
        c = box(f"Card{i}", (0.012, D - 0.26, H * 0.95), (x, 0, cz), card, 0.004, 2)
        c.rotation_euler = (0, lean, 0)
        col = DOMAIN[i % len(DOMAIN)] if i != 17 else "#22D67A"
        tm = principled(f"Tab{i}", srgb(col), rough=0.5)
        ty = (random.choice([-1, 0, 1]) * 0.42) if i != 17 else 0.0
        up = H * 0.95 / 2 + 0.09
        tab = box(f"Tab{i}", (0.02, 0.36, 0.2), (x + math.sin(lean) * up, ty, cz + math.cos(lean) * up), tm, 0.01, 2)
        tab.rotation_euler = (0, lean, 0)
    # the raised card: green glow edge (cited answer)
    floor(); std_lights(); camera((4.9, -3.9, 4.6), (0.0, 0.05, 0.6), lens=46)

def shot_cube():
    g = glass("Glass", (0.95, 0.99, 0.97, 1), 0.06, 0.42)
    core = principled("Core", srgb("#22D67A"), rough=0.2, emit=srgb("#22D67A"), emit_s=2.2)
    ink = principled("Ink", srgb("#151A18"), rough=0.35, coat=0.6)
    C = 1.6
    cube = box("GlassCube", (C, C, C), (0, 0, C / 2 + 0.14), g, 0.08, 6)
    cube.visible_shadow = False
    # inner: emissive node + orbit of domain spheres on a thin ring
    sphere("Core", 0.26, (0, 0, C / 2 + 0.14), core)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.55, minor_radius=0.008, location=(0, 0, C / 2 + 0.14), rotation=(math.radians(68), 0, math.radians(20)))
    ring = bpy.context.object; assign(ring, principled("Ring", srgb("#22D67A"), emit=srgb("#22D67A"), emit_s=2))
    for i in range(6):
        a = i / 6 * math.tau; v = Vector((0.55 * math.cos(a), 0.55 * math.sin(a), 0))
        v.rotate(ring.rotation_euler); v += Vector((0, 0, C / 2 + 0.14))
        sphere(f"Sat{i}", 0.07, v, principled(f"Sat{i}", srgb(DOMAIN[i + 1]), rough=0.25, emit=srgb(DOMAIN[i + 1]), emit_s=1.2))
        bpy.ops.mesh.primitive_cylinder_add(radius=0.006, depth=1, location=(0, 0, 0))
        e = bpy.context.object; d = v - Vector((0, 0, C / 2 + 0.14))
        e.scale = (1, 1, d.length); e.location = Vector((0, 0, C / 2 + 0.14)) + d / 2
        e.rotation_euler = d.to_track_quat("Z", "Y").to_euler(); assign(e, ring.data.materials[0])
    # ink plinth
    lathe("Plinth", [(0, -0.12), (1.25, -0.12), (1.3, -0.08), (1.3, 0.0), (0, 0.0)], ink, subsurf=1).location.z = 0.12
    # 5 port pegs on plinth = MCP tools
    for i in range(6):
        a = math.radians(-60 + i * 24); r = 1.12
        lathe(f"Peg{i}", [(0, 0), (0.05, 0), (0.05, 0.05), (0, 0.06)], principled(f"P{i}", srgb("#22D67A") if i == 2 else srgb("#2C3330"), rough=0.4), steps=32, subsurf=1).location = (r * math.sin(a), -r * math.cos(a), 0.11)
    floor(); std_lights(420, 110, 320); camera((4.3, -5.0, 4.4), (0, 0, 0.8), lens=50)

def shot_keycap():
    ink = bumpy(principled("Ceramic", srgb("#141A17"), rough=0.32, coat=0.8), 220, 0.015)
    gl = principled("Glaze", srgb("#22D67A"), rough=0.18, coat=1.0, emit=srgb("#22D67A"), emit_s=0.6)
    base = box("Keycap", (1.9, 1.9, 0.9), (0, 0, 0.45), ink, 0.22, 8)
    tp = base.modifiers.new("taper", "SIMPLE_DEFORM"); tp.deform_method = "TAPER"; tp.factor = -0.32; tp.deform_axis = "Z"
    # prompt caret as a beveled curve on top
    cu = bpy.data.curves.new("Caret", "CURVE"); cu.dimensions = "3D"; cu.bevel_depth = 0.085; cu.bevel_resolution = 6
    sp = cu.splines.new("POLY"); pts = [(-0.46, 0.4), (0.04, 0.0), (-0.46, -0.4)]
    sp.points.add(len(pts) - 1)
    for p, (x, y) in zip(sp.points, pts): p.co = (x, y, 0, 1)
    o = bpy.data.objects.new("Caret", cu); sc.collection.objects.link(o); o.location = (-0.05, 0, 0.93); o.rotation_euler.z = math.radians(15); assign(o, gl)
    cu2 = bpy.data.curves.new("Under", "CURVE"); cu2.dimensions = "3D"; cu2.bevel_depth = 0.085; cu2.bevel_resolution = 6
    s2 = cu2.splines.new("POLY"); s2.points.add(1); s2.points[0].co = (0.16, -0.4, 0, 1); s2.points[1].co = (0.5, -0.4, 0, 1)
    o2 = bpy.data.objects.new("Under", cu2); sc.collection.objects.link(o2); o2.location = (0, 0, 0.93); o2.rotation_euler.z = math.radians(15); assign(o2, gl)
    # two neighbour keys, paper-white, partly out of frame
    wht = bumpy(principled("Paper", srgb("#EFEADF"), rough=0.4, coat=0.5), 220, 0.01)
    for i, (x, y) in enumerate([(-2.15, 0.25), (0.2, 2.15)]):
        k = box(f"Key{i}", (1.9, 1.9, 0.9), (x, y, 0.45), wht, 0.22, 8)
        t = k.modifiers.new("taper", "SIMPLE_DEFORM"); t.deform_method = "TAPER"; t.factor = -0.32; t.deform_axis = "Z"
    floor(); std_lights(520, 120, 300); camera((3.0, -3.5, 6.0), (-0.25, 0.3, 0.45), lens=50)

{"drawer": shot_drawer, "cube": shot_cube, "keycap": shot_keycap}[SHOT]()
sc.render.filepath = OUT
if SAVE_BLEND: bpy.ops.wm.save_as_mainfile(filepath=SAVE_BLEND)
bpy.ops.render.render(write_still=True)
print("rendered", OUT)
