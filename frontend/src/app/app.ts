import { Component, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';

export interface FacturaDetalle {
  id_factura: string;
  nit_proveedor: string;
  fecha_factura: string;
  concepto: string;
  base_gravable: number | null;
  valor_iva: number | null;
  iva_esperado: number | null;
  valor_retencion: number | null;
  total_factura: number | null;
  total_esperado: number | null;
  estado: string;
  causas: string[];
}

export interface Resumen {
  total_facturas: number;
  facturas_correctas: number;
  facturas_con_inconsistencia: number;
  facturas_duplicadas: number;
  facturas_sin_contabilizar: number;
}

interface RespuestaProcesamiento {
  resumen: Resumen;
  detalle: FacturaDetalle[];
}

const API_URL = 'http://localhost:8000/api/procesar';

@Component({
  selector: 'app-root',
  imports: [CommonModule],
  templateUrl: './app.html',
  styleUrl: './app.css',
})
export class App {
  facturasFile: File | null = null;
  contabilidadFile: File | null = null;

  cargando = signal(false);
  error = signal('');
  resumen = signal<Resumen | null>(null);
  detalle = signal<FacturaDetalle[]>([]);
  filtroEstado = signal('Todos');

  detalleFiltrado = computed(() => {
    const estado = this.filtroEstado();
    const lista = this.detalle();
    if (estado === 'Todos') {
      return lista;
    }
    return lista.filter((f) => f.estado === estado);
  });

  constructor(private http: HttpClient) {}

  onFacturasSeleccionadas(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.facturasFile = input.files?.[0] ?? null;
  }

  onContabilidadSeleccionada(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.contabilidadFile = input.files?.[0] ?? null;
  }

  onFiltroChange(event: Event): void {
    const select = event.target as HTMLSelectElement;
    this.filtroEstado.set(select.value);
  }

  procesar(): void {
    this.error.set('');

    if (!this.facturasFile || !this.contabilidadFile) {
      this.error.set('Debes seleccionar el archivo de facturas y el de contabilidad.');
      return;
    }

    const formData = new FormData();
    formData.append('facturas_file', this.facturasFile);
    formData.append('contabilidad_file', this.contabilidadFile);

    this.cargando.set(true);
    this.resumen.set(null);
    this.detalle.set([]);

    this.http.post<RespuestaProcesamiento>(API_URL, formData).subscribe({
      next: (respuesta) => {
        this.resumen.set(respuesta.resumen);
        this.detalle.set(respuesta.detalle);
        this.cargando.set(false);
      },
      error: (err) => {
        this.error.set(
          err?.error?.detail ||
            'Ocurrió un error al procesar los archivos. Verifica que el backend esté corriendo en el puerto 8000.'
        );
        this.cargando.set(false);
      },
    });
  }
}
