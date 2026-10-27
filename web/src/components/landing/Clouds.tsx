import { SectionHeading } from "@/components/ui";

const ROWS = [
  ["Public access", "Public Access Block (4 flags)", "allowBlobPublicAccess off", "Public access prevention"],
  ["Public sharing", "Public ACL grants", "Public containers", "allUsers bindings"],
  ["Encryption", "Default encryption", "Always on", "Always on"],
  ["Versioning", "Bucket versioning", "Blob versioning", "Object versioning"],
  ["HTTPS only", "Policy denies plain HTTP", "Secure transfer required", "Not applicable"],
];

export function Clouds() {
  return (
    <section className="mx-auto max-w-6xl px-5 py-20" aria-labelledby="clouds">
      <SectionHeading
        kicker="Multi-cloud"
        title={<span id="clouds">Each cloud speaks its own dialect. ASPARe translates.</span>}
        sub="Native settings are mapped into one neutral model, so one rule and one safety gate protect everything."
        tone="sky"
      />
      <div className="card-flat mt-10 overflow-x-auto bg-white">
        <table className="w-full min-w-[640px] text-left text-[15px]">
          <caption className="sr-only">How each storage control maps across AWS, Azure and Google Cloud</caption>
          <thead>
            <tr className="border-b-2 border-ink text-sm">
              <th scope="col" className="px-5 py-4">Control</th>
              <th scope="col" className="bg-sun px-5 py-4">AWS S3</th>
              <th scope="col" className="bg-sky px-5 py-4">Azure Blob</th>
              <th scope="col" className="bg-mint px-5 py-4">Google Cloud</th>
            </tr>
          </thead>
          <tbody>
            {ROWS.map((r) => (
              <tr key={r[0]} className="border-b border-ink/15 last:border-0 hover:bg-sun-100">
                <th scope="row" className="px-5 py-4 font-bold">{r[0]}</th>
                <td className="px-5 py-4 text-muted">{r[1]}</td>
                <td className="px-5 py-4 text-muted">{r[2]}</td>
                <td className="px-5 py-4 text-muted">{r[3]}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
