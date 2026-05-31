export async function slide01(presentation, ctx) {
  const slide = presentation.slides.add();
  slide.background.fill = "#f7f3f8";
  ctx.addShape(slide, { x: 0, y: 0, width: 1280, height: 720, fill: "#72246c" });
  ctx.addText(slide, { x: 72, y: 82, width: 920, height: 72, text: "Store Intelligence API", fontSize: 54, bold: true, color: "#ffffff", typeface: ctx.fonts.title });
  ctx.addText(slide, { x: 74, y: 176, width: 860, height: 76, text: "CCTV-to-live retail analytics for offline conversion, queues, dwell, funnel, heatmap, and anomalies.", fontSize: 28, color: "#f6e7f5" });
  ctx.addShape(slide, { x: 72, y: 330, width: 250, height: 130, fill: "#ffffff", line: ctx.line("#ffffff", 0) });
  ctx.addText(slide, { x: 94, y: 350, width: 206, height: 44, text: "293", fontSize: 42, bold: true, color: "#72246c" });
  ctx.addText(slide, { x: 94, y: 404, width: 206, height: 38, text: "detected events", fontSize: 22, color: "#4c3d4c" });
  ctx.addShape(slide, { x: 350, y: 330, width: 250, height: 130, fill: "#ffffff", line: ctx.line("#ffffff", 0) });
  ctx.addText(slide, { x: 372, y: 350, width: 206, height: 44, text: "5/5", fontSize: 42, bold: true, color: "#72246c" });
  ctx.addText(slide, { x: 372, y: 404, width: 206, height: 38, text: "camera coverage", fontSize: 22, color: "#4c3d4c" });
  ctx.addShape(slide, { x: 628, y: 330, width: 250, height: 130, fill: "#ffffff", line: ctx.line("#ffffff", 0) });
  ctx.addText(slide, { x: 650, y: 350, width: 206, height: 44, text: "11", fontSize: 42, bold: true, color: "#72246c" });
  ctx.addText(slide, { x: 650, y: 404, width: 206, height: 38, text: "tests passing", fontSize: 22, color: "#4c3d4c" });
  ctx.addText(slide, { x: 74, y: 628, width: 920, height: 30, text: "Purplle Tech Challenge 2026 · Round 2", fontSize: 18, color: "#f6e7f5" });
  return slide;
}
