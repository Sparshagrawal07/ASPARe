const ITEMS = [
  ["AWS S3", "bg-sun"],
  ["Azure Blob Storage", "bg-sky"],
  ["Google Cloud Storage", "bg-mint"],
  ["Public access", "bg-coral text-white"],
  ["Encryption at rest", "bg-lilac"],
  ["Versioning", "bg-pink"],
  ["HTTPS only", "bg-peri text-white"],
  ["CIS Foundations", "bg-sun"],
  ["AWS FSBP", "bg-sky"],
  ["Least privilege", "bg-mint"],
  ["Full audit trail", "bg-lilac"],
];

export function Marquee() {
  const row = [...ITEMS, ...ITEMS];
  return (
    <div className="overflow-hidden border-y-2 border-ink bg-white py-4" aria-hidden="true">
      <div className="marquee gap-3 pr-3">
        {row.map(([label, tone], i) => (
          <span key={i} className={`shrink-0 rounded-full border-2 border-ink px-5 py-2 text-[15px] font-extrabold ${tone}`}>
            {label}
          </span>
        ))}
      </div>
    </div>
  );
}
