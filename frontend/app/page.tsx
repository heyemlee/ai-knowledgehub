export const runtime = "nodejs";

import { redirect } from 'next/navigation'

export default function RootPage() {
  // 重定向到默认语言（英文）
  redirect('/en-US')
}




