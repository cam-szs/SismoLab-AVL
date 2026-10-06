import { translateError } from "./errorMessages";

test("translates the duplicate-id error, including KeyError quotes", () => {
  expect(translateError("event 1 already exists as active")).toBe(
    "El evento #1 ya existe (activo); los identificadores no se reutilizan"
  );
  expect(translateError("'event 9 does not exist'")).toBe("No existe ningún evento con ID #9");
});

test("translates prefixed messages recursively", () => {
  expect(translateError("report 2 (event 7): unknown station 'ST-99'; scenario stations: ST-1, ST-2")).toBe(
    'Reporte 2 (evento 7): La estación "ST-99" no pertenece al escenario. Estaciones válidas: ST-1, ST-2'
  );
  expect(translateError("magnitude must have at most one decimal")).toBe(
    "La magnitud debe tener como máximo un decimal"
  );
});

test("leaves unknown messages unchanged", () => {
  expect(translateError("something new")).toBe("something new");
});
