# 3D models for the web

Format: **glTF Binary (.glb)**, compressed with Draco (geometry) and WebP/KTX2 (textures).

## Blender export (File > Export > glTF 2.0)
- Format: glTF Binary (.glb)
- Include: Selected Objects only (hide helpers, cameras, lights)
- Transform: +Y Up
- Mesh: Apply Modifiers ON, UVs ON, Normals ON, Tangents OFF, Vertex Colors OFF
- Mesh > Compression: Draco ON (level 6, position quantization 14)
- Material: Export, Image format = WebP (or Automatic)
- Animation: OFF unless needed

## Prep in Blender before exporting
1. Reduce polygons: car <= 150k tris, each UAV <= 100k tris. Use Decimate (Collapse) on curved parts; delete hidden internals (battery, wiring, bolts, CFD-only geometry).
2. Apply scale and rotation (Ctrl+A), set origin to the model centre, real-world scale in metres.
3. Merge objects/materials where you can: fewer than ~15 materials, fewer draw calls.
4. Textures: max 2048x2048 (1024 is enough for most parts). Bake complex shaders to a base-colour image; glTF only supports Principled BSDF.
5. No procedural nodes, no Cycles-only features: bake them or they won't export.

## Optional post-processing
`npx gltf-transform optimize in.glb out.glb --compress draco --texture-compress webp`

## Size targets
Under 5 MB per model so it loads fast on mobile. Check the result at https://gltf-viewer.donmccurdy.com or https://modelviewer.dev/editor/

## Usage (later)
Use Google's `<model-viewer>` web component (loads .glb with orbit controls, no build step).
