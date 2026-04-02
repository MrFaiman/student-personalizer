import { Input } from "@/components/ui/input";

export function MfaCodeInput(
  props: Omit<React.ComponentProps<typeof Input>, "dir" | "inputMode" | "autoComplete">,
) {
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

