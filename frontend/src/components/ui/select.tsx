import * as React from "react";
import {
  Select as RadixSelect,
  SelectTrigger as RadixSelectTrigger,
  SelectValue as RadixSelectValue,
  SelectContent as RadixSelectContent,
  SelectItem as RadixSelectItem,
  SelectGroup,
  SelectLabel,
  SelectSeparator,
  SelectViewport,
  SelectIcon
} from "@radix-ui/react-select";
import { cn } from "@/lib/utils";
import { ChevronDown } from "lucide-react";

const Select = RadixSelect;

const SelectTrigger = React.forwardRef<
  React.ElementRef<typeof RadixSelectTrigger>,
  React.ComponentPropsWithoutRef<typeof RadixSelectTrigger>
>(({ className, children, ...props }, ref) => (
  <RadixSelectTrigger
    ref={ref}
    className={cn("flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50", className)}
    {...props}
  >
    {children}
    <RadixSelectIcon asChild>
      <ChevronDown className="h-4 w-4 opacity-50" />
    </RadixSelectIcon>
  </RadixSelectTrigger>
));
SelectTrigger.displayName = RadixSelectTrigger.displayName;

const SelectValue = RadixSelectValue;
const SelectContent = RadixSelectContent;
const SelectItem = React.forwardRef<
  React.ElementRef<typeof RadixSelectItem>,
  React.ComponentPropsWithoutRef<typeof RadixSelectItem>
>(({ className, children, ...props }, ref) => (
  <RadixSelectItem
    ref={ref}
    className={cn("relative flex w-full cursor-default select-none items-center rounded-sm py-1.5 pl-2 pr-8 text-sm outline-none focus:bg-accent focus:text-accent-foreground data-[disabled]:pointer-events-none data-[disabled]:opacity-50", className)}
    {...props}
  >
    {children}
  </RadixSelectItem>
));
SelectItem.displayName = RadixSelectItem.displayName;

export {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
};
