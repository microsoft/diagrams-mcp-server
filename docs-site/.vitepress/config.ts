import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'Azure Diagram MCP Server',
  description: 'Generate professional infrastructure diagrams with AI',
  base: '/diagrams-mcp-server/',
  cleanUrls: true,
  appearance: 'dark',

  head: [
    ['link', { rel: 'icon', type: 'image/svg+xml', href: '/diagrams-mcp-server/favicon.svg' }],
  ],

  themeConfig: {
    logo: { light: '/logo-light.svg', dark: '/logo-dark.svg' },
    siteTitle: 'Azure Diagram MCP Server',

    nav: [
      { text: 'Home', link: '/' },
      { text: 'Guide', link: '/guide/getting-started' },
      {
        text: 'GitHub',
        link: 'https://github.com/microsoft/diagrams-mcp-server',
        target: '_blank',
      },
    ],

    sidebar: {
      '/guide/': [
        {
          text: 'Guide',
          items: [
            { text: 'Getting Started', link: '/guide/getting-started' },
            { text: 'Installation', link: '/guide/installation' },
            { text: 'Examples', link: '/guide/examples' },
          ],
        },
      ],
    },

    socialLinks: [
      { icon: 'github', link: 'https://github.com/microsoft/diagrams-mcp-server' },
    ],

    footer: {
      message: 'Released under the MIT License.',
      copyright: `Copyright © ${new Date().getFullYear()} Microsoft Corporation`,
    },

    search: {
      provider: 'local',
    },
  },

  vite: {
    css: {
      preprocessorOptions: {
        css: {},
      },
    },
  },
})
