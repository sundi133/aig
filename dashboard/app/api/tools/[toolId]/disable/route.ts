import { NextRequest, NextResponse } from "next/server";

import { api } from "@/lib/api";

export async function POST(_req: NextRequest, { params }: { params: { toolId: string } }) {
  try {
    const data = await api(`/v1/tools/${encodeURIComponent(params.toolId)}/disable`, { method: "POST" });
    return NextResponse.json(data);
  } catch (e) {
    return new NextResponse((e as Error).message, { status: 500 });
  }
}
