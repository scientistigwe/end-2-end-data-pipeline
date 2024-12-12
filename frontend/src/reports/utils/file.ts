  // src/report/utils/file.ts
  export function generateFileName(report: Report): string {
    const dateStr = new Date(report.createdAt)
      .toISOString()
      .split('T')[0];
    const sanitizedName = report.config.name
      .toLowerCase()
      .replace(/[^a-z0-9]/g, '-');
    return `${sanitizedName}-${dateStr}.${report.config.format}`;
  }
  
  export async function downloadBlob(blob: Blob, fileName: string): Promise<void> {
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = fileName;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  }
  