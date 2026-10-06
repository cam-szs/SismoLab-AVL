import SectionHeader from "./SectionHeader";

export default function WorkspaceCard({ label, title, className = "", children }) {
  return (
    <article className={`workspace-card ${className}`.trim()}>
      <SectionHeader label={label} title={title} />
      {children}
    </article>
  );
}
