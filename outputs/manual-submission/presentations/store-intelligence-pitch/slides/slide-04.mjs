export async function slide04(presentation, ctx) {
  const slide = presentation.slides.add();
  slide.background.fill = "#ffffff";
  ctx.addText(slide, { x: 60, y: 44, width: 260, height: 28, text: "API SURFACE", fontSize: 15, bold: true, color: "#72246c" });
  ctx.addText(slide, { x: 60, y: 82, width: 900, height: 56, text: "The API exposes the business questions reviewers will test.", fontSize: 36, bold: true, color: "#241824", typeface: ctx.fonts.title });
  const endpoints = [
    ["POST /events/ingest", "Validates, deduplicates, partial success"],
    ["GET /metrics", "Visitors, conversion, dwell, queue, abandon"],
    ["GET /funnel", "Entry → zone → billing → purchase"],
    ["GET /heatmap", "Zone frequency and dwell intensity"],
    ["GET /anomalies", "Queue spike, conversion drop, dead zones"],
    ["GET /health", "Service status and stale feed checks"]
  ];
  for (let i = 0; i < endpoints.length; i++) {
    const x = i % 2 === 0 ? 72 : 652;
    const y = 200 + Math.floor(i / 2) * 126;
    ctx.addShape(slide, { x, y, width: 500, height: 92, fill: "#f7f3f8", line: ctx.line("#e1d1e2", 1) });
    ctx.addText(slide, { x: x + 24, y: y + 18, width: 452, height: 28, text: endpoints[i][0], fontSize: 21, bold: true, color: "#72246c" });
    ctx.addText(slide, { x: x + 24, y: y + 52, width: 452, height: 24, text: endpoints[i][1], fontSize: 17, color: "#4c3d4c" });
  }
  return slide;
}
