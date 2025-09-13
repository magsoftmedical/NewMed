import { Component, OnInit, inject } from '@angular/core';
import { CommonModule, isPlatformBrowser } from '@angular/common';
import { RouterOutlet, RouterLink } from '@angular/router';
import { PLATFORM_ID } from '@angular/core';

@Component({
  selector: 'nm-root',
  standalone: true,
  imports: [CommonModule, RouterOutlet, RouterLink],
  templateUrl: './app.component.html',
})
export class AppComponent implements OnInit {
  private platformId = inject(PLATFORM_ID);
  private isBrowser = isPlatformBrowser(this.platformId);

  theme: 'light' | 'dark' = 'light';

  ngOnInit() {
    if (this.isBrowser) {
      const saved = (window.localStorage.getItem('theme') as 'light'|'dark'|null);
      this.theme = saved ?? (window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
      this.applyTheme();
    } else {
      // SSR: no tocar DOM ni localStorage
      this.theme = 'light';
    }
  }

  toggleTheme() {
    this.theme = this.theme === 'dark' ? 'light' : 'dark';
    if (this.isBrowser) {
      window.localStorage.setItem('theme', this.theme);
      this.applyTheme();
    }
  }

  private applyTheme() {
    if (!this.isBrowser) return;
    document.documentElement.classList.toggle('dark', this.theme === 'dark');
  }
}
