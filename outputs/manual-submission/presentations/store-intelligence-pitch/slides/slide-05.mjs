export async function slide05(presentation, ctx) {
  const slide = presentation.slides.add();
  slide.background.fill = "#241824";
  ctx.addText(slide, { x: 60, y: 44, width: 260, height: 28, text: "LIVE DEMO", fontSize: 15, bold: true, color: "#f6e7f5" });
  ctx.addText(slide, { x: 60, y: 86, width: 900, height: 62, text: "A replay script proves the dashboard is connected to ingestion.", fontSize: 38, bold: true, color: "#ffffff", typeface: ctx.fonts.title });
  ctx.addShape(slide, { x: 72, y: 210, width: 1120, height: 110, fill: "#352335", line: ctx.line("#7f5b80", 1) });
  ctx.addText(slide, { x: 102, y: 244, width: 1060, height: 42, text: "python pipeline/replay_events.py --input events/detected_events.jsonl --api-url http://localhost:8000 --batch-size 10 --delay 1", fontSize: 22, color: "#ffffff", typeface: ctx.fonts.mono });
  const bullets = [
    "Dashboard route: http://localhost:8000/dashboard",
    "Live JSON route: /stores/STORE_PURPLLE_001/live",
    "Final verification: 11 tests passing",
    "Primary event output: events/detected_events.jsonl"
  ];
  for (let i = 0; i < bullets.length; i++) {
    ctx.addText(slide, { x: 96, y: 392 + i * 54, width: 920, height: 34, text: `• ${bullets[i]}`, fontSize: 24, color: "#f6e7f5" });
  }
  return slide;
}
