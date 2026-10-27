import { currentUser } from "@/server/auth";
import { json } from "@/server/http";

export async function GET(request: Request) {
  return json({ user: await currentUser(request.headers) });
}
