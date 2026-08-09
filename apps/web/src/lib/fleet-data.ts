export interface DriverRecord {
  driverId: string;
  displayName: string;
  licenseClass: string;
  team: string;
  aggregateScore: number;
  status: "on_duty" | "off_duty" | "on_break";
  tripCount: number;
  totalDistanceKm: number;
  lastTripId: string | null;
  riskLevel: "low" | "medium" | "high" | "critical";
}

export interface VehicleRecord {
  vehicleId: string;
  plate: string;
  vehicleClass: string;
  lengthM: number;
  widthM: number;
  heightM: number;
  payloadKg: number;
  depot: string;
  status: "active" | "idle" | "maintenance" | "offline";
  tripCount: number;
  lastTripId: string | null;
  assignedDriverId: string | null;
}

export interface FleetTripRecord {
  tripId: string;
  vehicleId: string;
  driverId: string;
  source: "historical" | "live";
  status: "active" | "complete" | "processing" | "failed";
  orderCount: number;
  cargoClass: string;
  vehicleClass: string;
  routeName: string;
  score: number | null;
  severity: 1 | 2 | 3 | 4 | 5;
  distanceKm: number;
  startTime: string;
  endTime: string;
}

export interface FleetSummary {
  totalVehicles: number;
  totalDrivers: number;
  totalTrips: number;
  activeTrips: number;
  averageScore: number;
  criticalAlerts: number;
  fleetHealth: number;
}

export interface RiskInsight {
  category: string;
  count: number;
  severity: number;
  percentage: number;
}

export interface DriverRiskProfile {
  driverId: string;
  displayName: string;
  score: number;
  totalEvents: number;
  ttcEvents: number;
  harshBrakeEvents: number;
  speedingEvents: number;
  drowsinessEvents: number;
  riskTrend: "improving" | "stable" | "declining";
}

const mockDrivers: DriverRecord[] = [
  { driverId: "DRV-001", displayName: "Nguyen Van A", licenseClass: "B2", team: "HCM-Fleet-A", aggregateScore: 85, status: "on_duty", tripCount: 2, totalDistanceKm: 124, lastTripId: "T01d-Sample", riskLevel: "low" },
  { driverId: "DRV-002", displayName: "Tran Van B", licenseClass: "B2", team: "HCM-Fleet-B", aggregateScore: 72, status: "off_duty", tripCount: 2, totalDistanceKm: 98, lastTripId: "T05d-Sample", riskLevel: "medium" },
  { driverId: "DRV-003", displayName: "Le Thi C", licenseClass: "B2", team: "HCM-Fleet-A", aggregateScore: 91, status: "on_duty", tripCount: 2, totalDistanceKm: 156, lastTripId: "T06d-Sample", riskLevel: "low" },
  { driverId: "DRV-004", displayName: "Pham Van D", licenseClass: "B2", team: "HCM-Fleet-C", aggregateScore: 64, status: "on_break", tripCount: 1, totalDistanceKm: 67, lastTripId: "T04-Sample", riskLevel: "high" },
  { driverId: "DRV-005", displayName: "Hoang Van E", licenseClass: "C", team: "HCM-Fleet-B", aggregateScore: 78, status: "on_duty", tripCount: 2, totalDistanceKm: 210, lastTripId: "T03d-Sample", riskLevel: "medium" },
  { driverId: "DRV-006", displayName: "Ngo Thi F", licenseClass: "B2", team: "HCM-Fleet-A", aggregateScore: 58, status: "off_duty", tripCount: 2, totalDistanceKm: 88, lastTripId: "T10d-Sample", riskLevel: "critical" },
  { driverId: "DRV-007", displayName: "Vo Van G", licenseClass: "B2", team: "HCM-Fleet-C", aggregateScore: 93, status: "on_duty", tripCount: 2, totalDistanceKm: 142, lastTripId: "T09d-Sample", riskLevel: "low" },
  { driverId: "DRV-008", displayName: "Do Thi H", licenseClass: "B2", team: "HCM-Fleet-A", aggregateScore: 67, status: "on_break", tripCount: 1, totalDistanceKm: 72, lastTripId: "T04d-Sample", riskLevel: "high" },
  { driverId: "DRV-009", displayName: "Mai Van I", licenseClass: "B2", team: "HCM-Fleet-C", aggregateScore: 44, status: "off_duty", tripCount: 1, totalDistanceKm: 54, lastTripId: "T07d-Sample", riskLevel: "critical" },
  { driverId: "DRV-010", displayName: "Ly Van K", licenseClass: "C", team: "HCM-Fleet-B", aggregateScore: 81, status: "on_duty", tripCount: 1, totalDistanceKm: 180, lastTripId: "T08d-Sample", riskLevel: "low" },
];

const mockVehicles: VehicleRecord[] = [
  { vehicleId: "VH-DV-001", plate: "51A-12345", vehicleClass: "delivery_van", lengthM: 4.5, widthM: 1.8, heightM: 2.0, payloadKg: 800, depot: "DEPOT-HCM-01", status: "active", tripCount: 2, lastTripId: "T01d-Sample", assignedDriverId: "DRV-001" },
  { vehicleId: "VH-DV-002", plate: "51A-23456", vehicleClass: "delivery_van", lengthM: 4.5, widthM: 1.8, heightM: 2.0, payloadKg: 750, depot: "DEPOT-HCM-02", status: "idle", tripCount: 1, lastTripId: "T02-Sample", assignedDriverId: null },
  { vehicleId: "VH-DV-003", plate: "51A-34567", vehicleClass: "delivery_van", lengthM: 4.8, widthM: 1.9, heightM: 2.1, payloadKg: 900, depot: "DEPOT-HCM-01", status: "active", tripCount: 2, lastTripId: "T06d-Sample", assignedDriverId: "DRV-003" },
  { vehicleId: "VH-DV-004", plate: "51A-45678", vehicleClass: "delivery_van", lengthM: 4.6, widthM: 1.85, heightM: 2.05, payloadKg: 820, depot: "DEPOT-HCM-03", status: "maintenance", tripCount: 2, lastTripId: "T07d-Sample", assignedDriverId: null },
  { vehicleId: "VH-DV-005", plate: "51A-56789", vehicleClass: "truck", lengthM: 6.0, widthM: 2.2, heightM: 2.5, payloadKg: 2500, depot: "DEPOT-HCM-02", status: "active", tripCount: 1, lastTripId: "T05-Sample", assignedDriverId: "DRV-005" },
  { vehicleId: "VH-DV-006", plate: "51A-67890", vehicleClass: "delivery_van", lengthM: 4.5, widthM: 1.8, heightM: 2.0, payloadKg: 780, depot: "DEPOT-HCM-01", status: "offline", tripCount: 2, lastTripId: "T10d-Sample", assignedDriverId: null },
  { vehicleId: "VH-DV-007", plate: "51A-78901", vehicleClass: "sedan", lengthM: 4.2, widthM: 1.75, heightM: 1.45, payloadKg: 400, depot: "DEPOT-HCM-03", status: "active", tripCount: 2, lastTripId: "T09d-Sample", assignedDriverId: "DRV-007" },
  { vehicleId: "VH-DV-008", plate: "51A-89012", vehicleClass: "truck", lengthM: 7.0, widthM: 2.4, heightM: 2.8, payloadKg: 3500, depot: "DEPOT-HCM-02", status: "active", tripCount: 2, lastTripId: "T08d-Sample", assignedDriverId: "DRV-010" },
  { vehicleId: "VH-DV-009", plate: "51A-90123", vehicleClass: "delivery_van", lengthM: 4.7, widthM: 1.85, heightM: 2.1, payloadKg: 850, depot: "DEPOT-HCM-01", status: "idle", tripCount: 1, lastTripId: "T04d-Sample", assignedDriverId: null },
  { vehicleId: "VH-DV-010", plate: "51A-01234", vehicleClass: "delivery_van", lengthM: 4.5, widthM: 1.8, heightM: 2.0, payloadKg: 700, depot: "DEPOT-HCM-03", status: "active", tripCount: 1, lastTripId: "T05d-Sample", assignedDriverId: "DRV-002" },
];

const mockTrips: FleetTripRecord[] = [
  { tripId: "T01-Sample", vehicleId: "VH-DV-001", driverId: "DRV-001", source: "historical", status: "complete", orderCount: 12, cargoClass: "parcel", vehicleClass: "delivery_van", routeName: "HCM-District-1-Loop", score: 94, severity: 1, distanceKm: 62, startTime: "2026-07-15T06:00:00Z", endTime: "2026-07-15T08:30:00Z" },
  { tripId: "T02-Sample", vehicleId: "VH-DV-002", driverId: "DRV-002", source: "historical", status: "complete", orderCount: 8, cargoClass: "parcel", vehicleClass: "delivery_van", routeName: "HCM-District-3-Route", score: 71, severity: 3, distanceKm: 45, startTime: "2026-07-15T06:00:00Z", endTime: "2026-07-15T08:30:00Z" },
  { tripId: "T03-Sample", vehicleId: "VH-DV-003", driverId: "DRV-003", source: "historical", status: "complete", orderCount: 15, cargoClass: "parcel", vehicleClass: "delivery_van", routeName: "HCM-Rain-Night-Route", score: 71, severity: 3, distanceKm: 78, startTime: "2026-07-15T06:00:00Z", endTime: "2026-07-15T08:30:00Z" },
  { tripId: "T04-Sample", vehicleId: "VH-DV-004", driverId: "DRV-004", source: "historical", status: "complete", orderCount: 10, cargoClass: "parcel", vehicleClass: "delivery_van", routeName: "HCM-Highway-Route", score: 64, severity: 4, distanceKm: 67, startTime: "2026-07-15T06:00:00Z", endTime: "2026-07-15T08:30:00Z" },
  { tripId: "T05-Sample", vehicleId: "VH-DV-005", driverId: "DRV-005", source: "historical", status: "complete", orderCount: 6, cargoClass: "freight", vehicleClass: "truck", routeName: "HCM-Industrial-Zone", score: 78, severity: 2, distanceKm: 105, startTime: "2026-07-15T06:00:00Z", endTime: "2026-07-15T08:30:00Z" },
  { tripId: "T06-Sample", vehicleId: "VH-DV-006", driverId: "DRV-006", source: "historical", status: "complete", orderCount: 20, cargoClass: "parcel", vehicleClass: "delivery_van", routeName: "HCM-Suburban-Mixed", score: 52, severity: 5, distanceKm: 44, startTime: "2026-07-15T06:00:00Z", endTime: "2026-07-15T08:30:00Z" },
  { tripId: "T01d-Sample", vehicleId: "VH-DV-001", driverId: "DRV-001", source: "historical", status: "complete", orderCount: 18, cargoClass: "parcel", vehicleClass: "delivery_van", routeName: "HCM-Thu-Duc-Express", score: 85, severity: 2, distanceKm: 62, startTime: "2026-07-15T06:00:00Z", endTime: "2026-07-15T08:30:00Z" },
  { tripId: "T02d-Sample", vehicleId: "VH-DV-007", driverId: "DRV-007", source: "historical", status: "complete", orderCount: 25, cargoClass: "express", vehicleClass: "sedan", routeName: "HCM-Go-Vap-Shuttle", score: 93, severity: 1, distanceKm: 71, startTime: "2026-07-15T06:00:00Z", endTime: "2026-07-15T08:30:00Z" },
  { tripId: "T03d-Sample", vehicleId: "VH-DV-008", driverId: "DRV-005", source: "historical", status: "complete", orderCount: 3, cargoClass: "freight", vehicleClass: "truck", routeName: "HCM-Binh-Duong-Freight", score: 81, severity: 2, distanceKm: 105, startTime: "2026-07-15T06:00:00Z", endTime: "2026-07-15T08:30:00Z" },
  { tripId: "T04d-Sample", vehicleId: "VH-DV-009", driverId: "DRV-008", source: "historical", status: "complete", orderCount: 14, cargoClass: "parcel", vehicleClass: "delivery_van", routeName: "HCM-Phu-Nhuan-Loop", score: 67, severity: 3, distanceKm: 72, startTime: "2026-07-15T06:00:00Z", endTime: "2026-07-15T08:30:00Z" },
  { tripId: "T05d-Sample", vehicleId: "VH-DV-010", driverId: "DRV-002", source: "historical", status: "complete", orderCount: 9, cargoClass: "parcel", vehicleClass: "delivery_van", routeName: "HCM-Tan-Binh-Night", score: 72, severity: 3, distanceKm: 53, startTime: "2026-07-15T06:00:00Z", endTime: "2026-07-15T08:30:00Z" },
  { tripId: "T06d-Sample", vehicleId: "VH-DV-003", driverId: "DRV-003", source: "historical", status: "complete", orderCount: 16, cargoClass: "parcel", vehicleClass: "delivery_van", routeName: "HCM-Binh-Thanh-Mixed", score: 91, severity: 1, distanceKm: 78, startTime: "2026-07-15T06:00:00Z", endTime: "2026-07-15T08:30:00Z" },
  { tripId: "T07d-Sample", vehicleId: "VH-DV-004", driverId: "DRV-009", source: "historical", status: "complete", orderCount: 22, cargoClass: "parcel", vehicleClass: "delivery_van", routeName: "HCM-District-7-Mall", score: 44, severity: 5, distanceKm: 54, startTime: "2026-07-15T06:00:00Z", endTime: "2026-07-15T08:30:00Z" },
  { tripId: "T08d-Sample", vehicleId: "VH-DV-008", driverId: "DRV-010", source: "historical", status: "complete", orderCount: 2, cargoClass: "freight", vehicleClass: "truck", routeName: "HCM-Long-Thanh-Haul", score: 81, severity: 2, distanceKm: 180, startTime: "2026-07-15T06:00:00Z", endTime: "2026-07-15T08:30:00Z" },
  { tripId: "T09d-Sample", vehicleId: "VH-DV-007", driverId: "DRV-007", source: "historical", status: "complete", orderCount: 30, cargoClass: "express", vehicleClass: "sedan", routeName: "HCM-District-2-VIP", score: 93, severity: 1, distanceKm: 71, startTime: "2026-07-15T06:00:00Z", endTime: "2026-07-15T08:30:00Z" },
  { tripId: "T10d-Sample", vehicleId: "VH-DV-006", driverId: "DRV-006", source: "historical", status: "complete", orderCount: 7, cargoClass: "parcel", vehicleClass: "delivery_van", routeName: "HCM-Cu-Chi-Rural", score: 58, severity: 4, distanceKm: 44, startTime: "2026-07-15T06:00:00Z", endTime: "2026-07-15T08:30:00Z" },
];

export async function getDrivers(): Promise<DriverRecord[]> {
  try {
    const response = await fetch("http://localhost:8000/api/v1/drivers", { cache: "no-store" });
    if (!response.ok) return mockDrivers;
    const body = await response.json();
    if (!body.data?.length) return mockDrivers;
    return body.data.map((d: Record<string, unknown>) => ({
      driverId: d.driver_id as string,
      displayName: d.display_name as string,
      licenseClass: d.license_class as string,
      team: d.team as string,
      aggregateScore: (d.aggregate_score as number) ?? 0,
      status: (d.status as DriverRecord["status"]) ?? "off_duty",
      tripCount: (d.trip_count as number) ?? 0,
      totalDistanceKm: (d.total_distance_km as number) ?? 0,
      lastTripId: (d.last_trip_id as string) ?? null,
      riskLevel: (d.risk_level as DriverRecord["riskLevel"]) ?? "medium",
    }));
  } catch {
    return mockDrivers;
  }
}

export async function getVehicles(): Promise<VehicleRecord[]> {
  try {
    const response = await fetch("http://localhost:8000/api/v1/vehicles", { cache: "no-store" });
    if (!response.ok) return mockVehicles;
    const body = await response.json();
    if (!body.data?.length) return mockVehicles;
    return body.data.map((v: Record<string, unknown>) => ({
      vehicleId: v.vehicle_id as string,
      plate: v.plate as string,
      vehicleClass: (v.vehicle_class as string) ?? "delivery_van",
      lengthM: (v.length_m as number) ?? 0,
      widthM: (v.width_m as number) ?? 0,
      heightM: (v.height_m as number) ?? 0,
      payloadKg: (v.payload_kg as number) ?? 0,
      depot: (v.depot as string) ?? "",
      status: (v.status as VehicleRecord["status"]) ?? "offline",
      tripCount: (v.trip_count as number) ?? 0,
      lastTripId: (v.last_trip_id as string) ?? null,
      assignedDriverId: (v.assigned_driver_id as string) ?? null,
    }));
  } catch {
    return mockVehicles;
  }
}

export async function getFleetTripsData(): Promise<FleetTripRecord[]> {
  return mockTrips;
}

export function getFleetSummary(drivers: DriverRecord[], vehicles: VehicleRecord[], trips: FleetTripRecord[]): FleetSummary {
  const scores = trips.filter((t) => t.score !== null).map((t) => t.score as number);
  const averageScore = scores.length ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length) : 0;
  const criticalAlerts = trips.filter((t) => t.severity >= 4).length;

  return {
    totalVehicles: vehicles.length,
    totalDrivers: drivers.length,
    totalTrips: trips.length,
    activeTrips: vehicles.filter((v) => v.status === "active").length,
    averageScore,
    criticalAlerts,
    fleetHealth: Math.round(100 - (criticalAlerts / trips.length) * 100),
  };
}

export function getRiskInsights(trips: FleetTripRecord[]): RiskInsight[] {
  return [
    { category: "Short TTC events", count: trips.filter((t) => t.severity >= 4).length, severity: 4, percentage: Math.round((trips.filter((t) => t.severity >= 4).length / trips.length) * 100) },
    { category: "Harsh braking", count: trips.filter((t) => t.severity >= 3).length, severity: 3, percentage: Math.round((trips.filter((t) => t.severity >= 3).length / trips.length) * 100) },
    { category: "Speeding", count: trips.filter((t) => t.severity >= 2 && t.score !== null && t.score < 70).length, severity: 3, percentage: Math.round((trips.filter((t) => t.severity >= 2 && t.score !== null && t.score < 70).length / trips.length) * 100) },
    { category: "Driver distraction", count: trips.filter((t) => t.score !== null && t.score < 60).length, severity: 4, percentage: Math.round((trips.filter((t) => t.score !== null && t.score < 60).length / trips.length) * 100) },
    { category: "Lane departure", count: trips.filter((t) => t.severity >= 3).length, severity: 3, percentage: Math.round((trips.filter((t) => t.severity >= 3).length / trips.length) * 100) },
    { category: "Compound risk", count: trips.filter((t) => t.severity >= 5).length, severity: 5, percentage: Math.round((trips.filter((t) => t.severity >= 5).length / trips.length) * 100) },
  ];
}

export function getDriverRiskProfiles(drivers: DriverRecord[], trips: FleetTripRecord[]): DriverRiskProfile[] {
  return drivers.map((driver) => {
    const driverTrips = trips.filter((t) => t.driverId === driver.driverId);
    const totalEvents = driverTrips.length;
    return {
      driverId: driver.driverId,
      displayName: driver.displayName,
      score: driver.aggregateScore,
      totalEvents,
      ttcEvents: driverTrips.filter((t) => t.severity >= 4).length,
      harshBrakeEvents: driverTrips.filter((t) => t.severity >= 3).length,
      speedingEvents: driverTrips.filter((t) => t.severity >= 2 && t.score !== null && t.score < 70).length,
      drowsinessEvents: driverTrips.filter((t) => t.score !== null && t.score < 60).length,
      riskTrend: driver.aggregateScore >= 80 ? "improving" : driver.aggregateScore >= 65 ? "stable" : "declining",
    };
  });
}

export function getDriverTrips(driverId: string, trips: FleetTripRecord[]): FleetTripRecord[] {
  return trips.filter((t) => t.driverId === driverId);
}

export function getVehicleTrips(vehicleId: string, trips: FleetTripRecord[]): FleetTripRecord[] {
  return trips.filter((t) => t.vehicleId === vehicleId);
}

export function getDriverById(driverId: string, drivers: DriverRecord[]): DriverRecord | undefined {
  return drivers.find((d) => d.driverId === driverId);
}

export function getVehicleById(vehicleId: string, vehicles: VehicleRecord[]): VehicleRecord | undefined {
  return vehicles.find((v) => v.vehicleId === vehicleId);
}