export default function ActionButton({
  label,
  onClick,
  isLoading = false,
  secondary = false,
  type = "button",
  disabled = false,
  className = "",
  children,
}) {
  return (
    <button
      type={type}
      className={`action-button ${secondary ? "secondary" : ""} ${className}`.trim()}
      onClick={onClick}
      disabled={disabled || isLoading}
    >
      {isLoading ? "Cargando..." : children ?? label}
    </button>
  );
}
