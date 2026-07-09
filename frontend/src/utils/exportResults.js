// Export helpers for analysis results (extracted from AnalysisResults.jsx)

export const downloadResultsJson = (data, deepAnalysis, jobId) => {
  const exportData = { ...data }
  if (deepAnalysis) exportData.deep_analysis = deepAnalysis
  const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `analysis-${jobId}.json`
  a.click()
  URL.revokeObjectURL(url)
}

export const exportElementToPdf = async (elementId, filename) => {
  const { default: html2canvas } = await import('html2canvas')
  const { default: jsPDF } = await import('jspdf')
  const el = document.getElementById(elementId)
  if (!el) return
  const canvas = await html2canvas(el, { scale: 1.5, useCORS: true, logging: false })
  const imgData = canvas.toDataURL('image/png')
  const pdf = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' })
  const pageW = pdf.internal.pageSize.getWidth()
  const pageH = pdf.internal.pageSize.getHeight()
  const margin = 10
  const imgW = pageW - margin * 2
  const imgH = (canvas.height * imgW) / canvas.width
  let y = margin
  let remaining = imgH
  while (remaining > 0) {
    if (y !== margin) pdf.addPage()
    pdf.addImage(imgData, 'PNG', margin, y === margin ? margin : -(imgH - remaining), imgW, imgH)
    remaining -= (pageH - margin * 2)
    y = margin
  }
  pdf.save(filename)
}
