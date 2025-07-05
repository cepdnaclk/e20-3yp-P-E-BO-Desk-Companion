import { render, fireEvent } from "@testing-library/react-native";
import SignUpScreen from "../screens/SignUpScreen"; // Adjust path as needed
import { auth } from "../services/firebase";
import { getDatabase, ref, set } from "firebase/database";

// Mock Firebase
jest.mock("firebase/auth", () => ({
  createUserWithEmailAndPassword: jest.fn(),
}));
jest.mock("firebase/database", () => ({
  getDatabase: jest.fn(),
  ref: jest.fn(),
  set: jest.fn(),
}));
jest.mock("../services/firebase", () => ({
  auth: jest.fn(),
}));
jest.mock("@expo/vector-icons", () => ({
  Ionicons: jest.fn(() => null),
}));
jest.mock("../components/PopupModal", () => jest.fn(() => null));

// Mock navigation
const mockNavigation = {
  reset: jest.fn(),
  replace: jest.fn(),
};

test("rejects invalid email", () => {
  const { getByTestId } = render(<SignUpScreen navigation={mockNavigation} />);
  fireEvent.changeText(getByTestId("email-input"), "user@");
  fireEvent.press(getByTestId("submit-button"));
  expect(getByTestId("error-message")).toHaveTextContent(
    "Invalid email format"
  );
});
