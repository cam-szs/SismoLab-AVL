import { fireEvent, render, screen } from "@testing-library/react";
import App from "./App.jsx";
import ActionButton from "./components/ActionButton.jsx";
import AssociationItem from "./components/AssociationItem.jsx";
import ClockControls from "./components/ClockControls.jsx";
import EmptyState from "./components/EmptyState.jsx";
import EventList from "./components/EventList.jsx";
import MapPoint from "./components/MapPoint.jsx";
import MetricCard from "./components/MetricCard.jsx";
import ModeSwitcher from "./components/ModeSwitcher.jsx";
import NodePanel from "./components/NodePanel.jsx";
import ParameterGrid from "./components/ParameterGrid.jsx";
import QueueItem from "./components/QueueItem.jsx";
import SectionHeader from "./components/SectionHeader.jsx";
import WorkspaceCard from "./components/WorkspaceCard.jsx";

test("App renders the main observatory shell", () => {
  render(<App />);

  expect(screen.getByText(/SismoLab/i)).toBeInTheDocument();
  expect(screen.getByText(/OBSERVATORIO SISMICO SIMULADO/i)).toBeInTheDocument();
});

test("App renders the audit and persistent versions controls", () => {
  render(<App />);

  expect(screen.getByText("AUDITORÍA")).toBeInTheDocument();
  expect(screen.getByText("VERSIONES")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Guardar versión" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Actualizar lista" })).toBeInTheDocument();
});

test("EventList shows event details and calls the recovery action", () => {
  const handleRecover = vi.fn();

  render(
    <EventList
      title="Archivados"
      events={[
        { id: 7, magnitude: 4.5, depth_km: 10, revision: 2, status: "archived" },
      ]}
      kind="archive"
      onRecover={handleRecover}
    />
  );

  expect(screen.getByText(/Evento #7/i)).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: /recuperar/i }));
  expect(handleRecover).toHaveBeenCalledWith(7);
});

test("SectionHeader renders section metadata consistently", () => {
  render(<SectionHeader label="ESTRUCTURA" title="AVL VS BST" />);

  expect(screen.getByText("ESTRUCTURA")).toBeInTheDocument();
  expect(screen.getByText("AVL VS BST")).toBeInTheDocument();
});

test("MetricCard renders a single metric with its value and label", () => {
  render(<MetricCard label="Reloj" value={12} />);

  expect(screen.getByText("12")).toBeInTheDocument();
  expect(screen.getByText("Reloj")).toBeInTheDocument();
});

test("ActionButton renders a primary action and respects its state", () => {
  render(
    <ActionButton
      label="Guardar en backend"
      isLoading={false}
      secondary={false}
      onClick={() => {}}
    />
  );

  expect(screen.getByRole("button", { name: "Guardar en backend" })).toBeInTheDocument();
  expect(screen.getByRole("button")).not.toBeDisabled();
});

test("ModeSwitcher highlights the selected mode and triggers updates", () => {
  const onChange = vi.fn();

  render(
    <ModeSwitcher
      value="normal"
      modes={[{ value: "normal", label: "Normal" }, { value: "stress", label: "Estrés" }]}
      onChange={onChange}
    />
  );

  const stressButton = screen.getByRole("button", { name: "Estrés" });
  expect(stressButton).toBeInTheDocument();
  fireEvent.click(stressButton);
  expect(onChange).toHaveBeenCalledWith("stress");
});

test("ClockControls advances by the hours typed by the user", () => {
  const onAdvance = vi.fn();

  render(<ClockControls onAdvance={onAdvance} simulationTime="2026-10-01T10:00:00Z" />);

  expect(screen.getByText("2026-10-01 10:00:00 UTC")).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Avanzar (horas)"), { target: { value: "80" } });
  fireEvent.click(screen.getByRole("button", { name: "Avanzar reloj" }));
  expect(onAdvance).toHaveBeenCalledWith(80);
});

test("ClockControls ignores non-positive or fractional hours", () => {
  const onAdvance = vi.fn();

  render(<ClockControls onAdvance={onAdvance} />);

  const input = screen.getByLabelText("Avanzar (horas)");
  for (const value of ["0", "-3", "1.5"]) {
    fireEvent.change(input, { target: { value } });
    fireEvent.submit(input.closest("form"));
  }
  expect(onAdvance).not.toHaveBeenCalled();
});

test("ParameterGrid renders configured inputs and updates values", () => {
  const onChange = vi.fn();

  render(
    <ParameterGrid
      parameters={[
        { key: "W", label: "Ventana (h)", value: 6 },
        { key: "R", label: "Distancia (km)", value: 8 },
      ]}
      onChange={onChange}
    />
  );

  const input = screen.getByLabelText("W · Ventana (h)");
  fireEvent.change(input, { target: { value: "12" } });
  expect(onChange).toHaveBeenCalled();
});

test("QueueItem renders the item metadata and identifier", () => {
  render(<QueueItem id={15} station="A1" magnitude={4.2} depth={9.8} />);

  expect(screen.getByText("#15")).toBeInTheDocument();
  expect(screen.getByText("A1")).toBeInTheDocument();
  expect(screen.getByText("M 4.2 · 9.8 km")).toBeInTheDocument();
});

test("AssociationItem renders the association metadata", () => {
  render(<AssociationItem sourceId={10} referenceId={22} distance={18.5} timeHours={3.2} />);

  expect(screen.getByText("#10")).toBeInTheDocument();
  expect(screen.getByText("→ #22")).toBeInTheDocument();
  expect(screen.getByText("18.5 km · 3.2 h")).toBeInTheDocument();
});

test("MapPoint renders with the provided position and event id", () => {
  render(<MapPoint id={7} left={25} top={40} />);

  const point = screen.getByTitle("Evento #7");
  expect(point).toBeInTheDocument();
  expect(point).toHaveStyle({ left: "25%", top: "40%" });
});

test("NodePanel exposes the selected node metadata and actions", () => {
  render(
    <NodePanel
      node={{ key: { magnitude_tenths: 22, depth_km: 10 }, event: { id: 8, magnitude: 2.2, depth_km: 10 } }}
      onClose={() => {}}
      onReview={() => {}}
      onArchive={() => {}}
      onDelete={() => {}}
      busy={false}
    />
  );

  expect(screen.getByText("Nodo #8")).toBeInTheDocument();
  expect(screen.getByText("M 2.2 · 10.0 km")).toBeInTheDocument();
});

test("WorkspaceCard renders the section shell and children", () => {
  render(
    <WorkspaceCard title="Mapa" label="TERRITORIO">
      <div>Contenido</div>
    </WorkspaceCard>
  );

  expect(screen.getByText("TERRITORIO")).toBeInTheDocument();
  expect(screen.getByText("Mapa")).toBeInTheDocument();
  expect(screen.getByText("Contenido")).toBeInTheDocument();
});

test("EmptyState renders the provided message", () => {
  render(<EmptyState message="Sin reportes pendientes" compact />);

  expect(screen.getByText("Sin reportes pendientes")).toBeInTheDocument();
});
