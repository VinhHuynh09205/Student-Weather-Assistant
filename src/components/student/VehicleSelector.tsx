import type { VehicleType } from "../../types/weather";
import { vehicleOptions } from "../../utils/formatters";
import { Card } from "../common/Card";

type VehicleSelectorProps = {
  selectedVehicle: VehicleType;
  onChange: (vehicle: VehicleType) => void;
  framed?: boolean;
};

export function VehicleSelector({ framed = true, onChange, selectedVehicle }: VehicleSelectorProps) {
  const grid = (
    <div className="vehicle-grid">
      {vehicleOptions.map((vehicle) => (
        <button
          className={`vehicle-card-btn ${selectedVehicle === vehicle.id ? "selected" : ""}`}
          key={vehicle.id}
          type="button"
          onClick={() => onChange(vehicle.id)}
        >
          <span className="vehicle-icon">{vehicle.icon}</span>
          <span className="vehicle-name">{vehicle.label}</span>
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
