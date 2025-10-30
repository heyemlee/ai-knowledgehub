# Frontend - Next.js 14

## 安装依赖

```bash
npm install
# 或
yarn install
# 或
pnpm install
```

## 开发模式

```bash
npm run dev
```

访问: http://localhost:3000

## 构建生产版本

```bash
npm run build
npm start
```

## 环境变量

创建 `.env.local` 文件：

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_MODE=development
```

## 部署到 Vercel

1. 连接 GitHub 仓库到 Vercel
2. 配置环境变量
3. 自动部署

