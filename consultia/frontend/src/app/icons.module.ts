import { NgModule } from '@angular/core';
import { LucideAngularModule, Mic, Pause, Trash2, FileText, File } from 'lucide-angular';

@NgModule({
  // pick(...) SOLO aquí (en un NgModule)
  imports: [LucideAngularModule.pick({ Mic, Pause, Trash2, FileText, File })],
  // re-exporta el módulo para poder usar <lucide-icon ...> en componentes
  exports: [LucideAngularModule],
})
export class IconsModule {}
