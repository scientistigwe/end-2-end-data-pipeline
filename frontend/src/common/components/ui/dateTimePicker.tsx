import * as React from "react";
import { Calendar } from "@/common/components/ui/calendar";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/common/components/ui/popover";
import { Button } from "@/common/components/ui/button";
import { Input } from "@/common/components/ui/inputs/input";
import { cn } from "@/common/utils/cn";
import { Calendar as CalendarIcon } from "lucide-react";
import { format, parseISO } from "date-fns";

interface DateTimePickerProps {
  value?: Date | string;
  onChange?: (date: Date) => void;
  className?: string;
  error?: string;
  id?: string;
  name?: string;
}

export function DateTimePicker({ 
  value,
  onChange,
  className,
  error,
  id,
  name 
}: DateTimePickerProps) {
  // Parse the initial value if it's a string
  const parseDate = (value: Date | string | undefined): Date | undefined => {
    if (!value) return undefined;
    if (value instanceof Date) return value;
    try {
      return parseISO(value);
    } catch (e) {
      console.error("Failed to parse date:", e);
      return undefined;
    }
  };

  const [selectedDate, setSelectedDate] = React.useState<Date | undefined>(parseDate(value));
  const [open, setOpen] = React.useState(false);

  // Separate hours and minutes
  const hours = selectedDate ? selectedDate.getHours() : 0;
  const minutes = selectedDate ? selectedDate.getMinutes() : 0;

  const handleDateSelect = (date: Date | undefined) => {
    if (date) {
      const newDate = new Date(date);
      newDate.setHours(hours);
      newDate.setMinutes(minutes);
      setSelectedDate(newDate);
      onChange?.(newDate);
    }
  };

  const handleTimeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (selectedDate && e.target.value) {
      const [newHours, newMinutes] = e.target.value.split(':').map(Number);
      const newDate = new Date(selectedDate);
      newDate.setHours(newHours);
      newDate.setMinutes(newMinutes);
      setSelectedDate(newDate);
      onChange?.(newDate);
    }
  };

  // Update selected date when value changes externally
  React.useEffect(() => {
    const parsedDate = parseDate(value);
    if (parsedDate && (!selectedDate || parsedDate.getTime() !== selectedDate.getTime())) {
      setSelectedDate(parsedDate);
    }
  }, [value, selectedDate]);

  const displayDate = selectedDate ? format(selectedDate, "PPP p") : "Pick a date";

  return (
    <div className={cn("grid gap-2", className)}>
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            id={id}
            name={name}
            type="button"
            variant="outline"
            className={cn(
              "w-full justify-start text-left font-normal",
              !selectedDate && "text-muted-foreground",
              error && [
                "border-destructive",
                "focus-visible:ring-destructive",
              ]
            )}
            aria-invalid={!!error}
          >
            <CalendarIcon className={cn(
              "mr-2 h-4 w-4",
              error && "text-destructive"
            )} />
            <span>{displayDate}</span>
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-auto p-0" align="start">
          <Calendar
            mode="single"
            selected={selectedDate}
            onSelect={handleDateSelect}
            initialFocus
          />
          <div className="p-3 border-t border-border">
            <Input
              type="time"
              value={`${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`}
              onChange={handleTimeChange}
              className="w-full"
            />
          </div>
        </PopoverContent>
      </Popover>
      {error && (
        <p className="text-sm text-destructive">{error}</p>
      )}
    </div>
  );
}