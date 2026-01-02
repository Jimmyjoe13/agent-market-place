import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
  ]),
  // Custom rules for CI compatibility
  {
    rules: {
      // Allow explicit any in some cases (API responses, dynamic data)
      "@typescript-eslint/no-explicit-any": "warn",
      // Allow unused vars prefixed with underscore
      "@typescript-eslint/no-unused-vars": ["warn", { 
        argsIgnorePattern: "^_",
        varsIgnorePattern: "^_"
      }],
      // Allow empty functions (event handlers, etc.)
      "@typescript-eslint/no-empty-function": "off",
      // Allow French apostrophes in text content
      "react/no-unescaped-entities": "off",
      // Disable React Compiler rules temporarily (React 19 migration)
      // TODO: Fix these issues progressively
      "react-compiler/react-compiler": "off",
      // Downgrade react-hooks exhaustive-deps to warning (needs gradual fixes)
      "react-hooks/exhaustive-deps": "warn",
    },
  },
]);

export default eslintConfig;

