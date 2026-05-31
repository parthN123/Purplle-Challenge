export async function slide02(presentation, ctx) {
  const slide = presentation.slides.add();
  slide.background.fill = "#ffffff";
  ctx.addText(slide, { x: 60, y: 44, width: 260, height: 28, text: "ARCHITECTURE", fontSize: 15, bold: true, color: "#72246c" });
  ctx.addText(slide, { x: 60, y: 82, width: 840, height: 56, text: "The pipeline connects raw footage to live operational metrics.", fontSize: 36, bold: true, color: "#241824", typeface: ctx.fonts.title });
  const steps = [
    ["Raw CCTV", "Five supplied MP4 clips"],
    ["Detection", "YOLOv8 + centroid tracking"],
    ["Event Stream", "Schema-valid JSONL"],
    ["API", "FastAPI + SQLite ingestion"],
    ["Dashboard", "2-second live polling"]
  ];
  for (let i = 0; i < steps.length; i++) {
    const x = 72 + i * 232;
    ctx.addShape(slide, { x, y: 260, width: 180, height: 160, fill: i % 2 === 0 ? "#f7f3f8" : "#f0e3f0", line: ctx.line("#d8c5d9", 1) });
    ctx.addText(slide, { x: x + 18, y: 284, width: 144, height: 34, text: steps[i][0], fontSize: 24, bold: true, color: "#72246c" });
    ctx.addText(slide, { x: x + 18, y: 334, width: 144, height: 60, text: steps[i][1], fontSize: 18, color: "#4c3d4c" });
    if (i < steps.length - 1) ctx.addText(slide, { x: x + 190, y: 318, width: 32, height: 36, text: "→", fontSize: 28, color: "#72246c" });
  }
  ctx.addText(slide, { x: 72, y: 540, width: 1050, height: 60, text: "The same event contract powers scoring endpoints, replay demos, and the live dashboard, keeping batch and simulated real-time paths aligned.", fontSize: 24, color: "#241824" });
  return slide;
}
