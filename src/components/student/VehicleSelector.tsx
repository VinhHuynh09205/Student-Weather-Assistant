import type { VehicleType } from "../../types/weather";
import { vehicleLabels } from "../../utils/formatters";
import { Card } from "../common/Card";

const vehicles: Array<{ id: VehicleType; icon: string }> = [
  { id: "motorbike", icon: "🏍️" },
  { id: "bus", icon: "🚌" },
  { id: "walking", icon: "🚶" },
  { id: "bicycle", icon: "🚲" },
];

type VehicleSelectorProps = {
  selectedVehicle: VehicleType;
  onChange: (vehicle: VehicleType) => void;
  framed?: boolean;
};

export function VehicleSelector({ framed = true, onChange, selectedVehicle }: VehicleSelectorProps) {
  const grid = (
    <div className="vehicle-grid">
      {vehicles.map((vehicle) => (
        <button
          className={`vehicle-card-btn ${selectedVehicle === vehicle.id ? "selected" : ""}`}
          key={vehicle.id}
          type="button"
          onClick={() => onChange(vehicle.id)}
        >
          <span className="vehicle-icon">{vehicle.icon}</span>
          <span className="vehicle-name">{vehicleLabels[vehicle.id]}</span>
        </button>
      ))}
    </div>
  );

  if (!framed) {
    return grid;
  }

  return (
    <Card className="selector-card vehicle-card" title="Phương tiện di chuyển">
      {grid}
    </Card>
  );
}
