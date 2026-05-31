export async function slide03(presentation, ctx) {
  const slide = presentation.slides.add();
  slide.background.fill = "#f7f3f8";
  ctx.addText(slide, { x: 60, y: 44, width: 260, height: 28, text: "DETECTION OUTPUT", fontSize: 15, bold: true, color: "#72246c" });
  ctx.addText(slide, { x: 60, y: 82, width: 920, height: 56, text: "All five cameras now produce auditable events.", fontSize: 36, bold: true, color: "#241824", typeface: ctx.fonts.title });
  const cams = [["CAM_1",19],["CAM_2",124],["CAM_3",79],["CAM_4",6],["CAM_5",65]];
  const max = 124;
  for (let i = 0; i < cams.length; i++) {
    const y = 210 + i * 74;
    ctx.addText(slide, { x: 96, y, width: 110, height: 32, text: cams[i][0], fontSize: 22, bold: true, color: "#241824" });
    ctx.addShape(slide, { x: 220, y: y + 5, width: 760, height: 24, fill: "#eadfea", line: ctx.line("#eadfea", 0) });
    ctx.addShape(slide, { x: 220, y: y + 5, width: Math.max(42, 760 * cams[i][1] / max), height: 24, fill: "#72246c", line: ctx.line("#72246c", 0) });
    ctx.addText(slide, { x: 1000, y: y - 2, width: 80, height: 32, text: String(cams[i][1]), fontSize: 22, bold: true, color: "#72246c" });
  }
  ctx.addText(slide, { x: 96, y: 610, width: 980, height: 40, text: "CAM_4 uses low-confidence billing fallback rows when raw detections are unreliable, preserving coverage without pretending confidence is high.", fontSize: 20, color: "#4c3d4c" });
  return slide;
}
