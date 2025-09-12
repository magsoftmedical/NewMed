import { ApplicationConfig } from '@angular/core';
import { provideRouter } from '@angular/router';
import { routes } from './app.routes';
import { provideHttpClient, withInterceptorsFromDi, withFetch } from '@angular/common/http';

export const appConfig: ApplicationConfig = {
  providers: [
    provideRouter(routes),
    // ✅ HttpClient usando fetch + interceptores DI
    provideHttpClient(
      withFetch(),
      withInterceptorsFromDi(),
    ),
  ],
};
