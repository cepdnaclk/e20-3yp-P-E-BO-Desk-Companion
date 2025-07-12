// Simplified babel.config.js (if Flow is not used)
module.exports = {
  presets: [
    ["@babel/preset-env", { targets: { node: "current" } }],
    "@babel/preset-react",
    "metro-react-native-babel-preset",
  ],
};
