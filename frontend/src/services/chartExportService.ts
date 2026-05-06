/**
 * 图表导出服务
 * 支持PNG、JPG、PDF、SVG、Excel等多种格式导出
 */

import type { ECharts } from 'echarts'
import type { ExportFormat, ChartData, ChartConfig, BatchExportConfig } from '@/types/chart'
import jsPDF from 'jspdf'
import * as XLSX from 'xlsx'

export class ChartExportService {
  /**
   * 导出图表为图片格式（PNG/JPG/SVG）
   */
  exportAsImage(
    chartInstance: ECharts,
    format: 'png' | 'jpg' | 'svg',
    filename: string = 'chart'
  ): void {
    const url = chartInstance.getDataURL({
      type: format === 'jpg' ? 'jpeg' : format,
      pixelRatio: 2,
      backgroundColor: '#fff'
    })

    this.downloadFile(url, `${filename}.${format}`)
  }

  /**
   * 导出图表为PDF
   */
  async exportAsPDF(
    chartInstance: ECharts,
    filename: string = 'chart',
    options?: {
      title?: string
      orientation?: 'portrait' | 'landscape'
      format?: 'a4' | 'letter'
    }
  ): Promise<void> {
    const imageUrl = chartInstance.getDataURL({
      type: 'png',
      pixelRatio: 2,
      backgroundColor: '#fff'
    })

    const pdf = new jsPDF({
      orientation: options?.orientation || 'landscape',
      unit: 'mm',
      format: options?.format || 'a4'
    })

    // 添加标题
    if (options?.title) {
      pdf.setFontSize(16)
      pdf.text(options.title, 10, 10)
    }

    // 计算图片尺寸以适应页面
    const pageWidth = pdf.internal.pageSize.getWidth()
    const pageHeight = pdf.internal.pageSize.getHeight()
    const margin = 10
    const titleHeight = options?.title ? 15 : 0

    const imgWidth = pageWidth - 2 * margin
    const imgHeight = pageHeight - 2 * margin - titleHeight

    // 添加图表图片
    pdf.addImage(
      imageUrl,
      'PNG',
      margin,
      margin + titleHeight,
      imgWidth,
      imgHeight
    )

    // 保存PDF
    pdf.save(`${filename}.pdf`)
  }

  /**
   * 导出图表数据为Excel
   */
  exportAsExcel(
    data: ChartData,
    filename: string = 'chart-data'
  ): void {
    // 创建工作簿
    const wb = XLSX.utils.book_new()

    // 准备数据：第一行是列名，后续行是数据
    const wsData = [data.columns, ...data.rows]

    // 创建工作表
    const ws = XLSX.utils.aoa_to_sheet(wsData)

    // 设置列宽
    const colWidths = data.columns.map(() => ({ wch: 15 }))
    ws['!cols'] = colWidths

    // 添加工作表到工作簿
    XLSX.utils.book_append_sheet(wb, ws, 'Chart Data')

    // 导出文件
    XLSX.writeFile(wb, `${filename}.xlsx`)
  }

  /**
   * 批量导出图表
   */
  async batchExport(config: BatchExportConfig): Promise<void> {
    const { charts, format, filename = 'charts', includeData = false } = config

    if (format === 'pdf') {
      // PDF批量导出：所有图表合并到一个PDF
      await this.batchExportAsPDF(charts, filename)
    } else if (format === 'excel') {
      // Excel批量导出：所有数据合并到一个Excel的多个sheet
      this.batchExportAsExcel(charts, filename)
    } else {
      // 图片格式：分别导出每个图表
      // 注意：这里需要图表实例，实际使用时需要传入
      console.warn('Batch export for image formats requires chart instances')
    }
  }

  /**
   * 批量导出为PDF（多页）
   */
  private async batchExportAsPDF(
    charts: ChartConfig[],
    filename: string
  ): Promise<void> {
    const pdf = new jsPDF({
      orientation: 'landscape',
      unit: 'mm',
      format: 'a4'
    })

    for (let i = 0; i < charts.length; i++) {
      if (i > 0) {
        pdf.addPage()
      }

      // 添加图表标题
      pdf.setFontSize(14)
      pdf.text(charts[i].name || `Chart ${i + 1}`, 10, 10)

      // 注意：这里需要图表的图片数据
      // 实际使用时需要先渲染图表获取图片
      pdf.setFontSize(10)
      pdf.text(`Chart Type: ${charts[i].type}`, 10, 20)
      pdf.text(`Created: ${charts[i].createdAt?.toLocaleDateString() || 'N/A'}`, 10, 25)
    }

    pdf.save(`${filename}.pdf`)
  }

  /**
   * 批量导出为Excel（多sheet）
   */
  private batchExportAsExcel(
    charts: ChartConfig[],
    filename: string
  ): void {
    const wb = XLSX.utils.book_new()

    charts.forEach((chart, index) => {
      const sheetName = chart.name || `Chart ${index + 1}`
      const wsData = [chart.data.columns, ...chart.data.rows]
      const ws = XLSX.utils.aoa_to_sheet(wsData)

      // 设置列宽
      const colWidths = chart.data.columns.map(() => ({ wch: 15 }))
      ws['!cols'] = colWidths

      XLSX.utils.book_append_sheet(wb, ws, sheetName.substring(0, 31)) // Excel sheet名称限制31字符
    })

    XLSX.writeFile(wb, `${filename}.xlsx`)
  }

  /**
   * 下载文件辅助方法
   */
  private downloadFile(url: string, filename: string): void {
    const link = document.createElement('a')
    link.download = filename
    link.href = url
    link.click()
  }
}

// 导出单例
export const chartExportService = new ChartExportService()
