import { toNextJsHandler } from "better-auth/next-js";
import { getAuth } from "@/server/auth";

async function handlers() {
  return toNextJsHandler(await getAuth());
}

export async function GET(request: Request) {
  return (await handlers()).GET(request);
}

export async function POST(request: Request) {
  return (await handlers()).POST(request);
}
