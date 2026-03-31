import { Input, type InputProps } from "@/components/ui/input";

export function MfaCodeInput(props: Omit<InputProps, "dir" | "inputMode" | "autoComplete">) {
  return (
    <Input
      {...props}
      dir="ltr"
      inputMode="numeric"
      autoComplete="one-time-code"
      placeholder={props.placeholder ?? "000000"}
    />
  );
}

