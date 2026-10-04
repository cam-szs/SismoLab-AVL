import SectionHeader from "./SectionHeader";

export default function WorkspaceCard({ index, label, title, className = "", children }) {
  return (
    <article className={`workspace-card ${className}`.trim()}>
      <SectionHeader index={index} label={label} title={title} />
      {children}
    </article>
  );
}
