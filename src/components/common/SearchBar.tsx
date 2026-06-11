import { Search } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";

type SearchBarProps = {
  city: string;
  disabled?: boolean;
  inputLabel?: string;
  onSearch: (city: string) => void;
  placeholder?: string;
  resetKey?: string;
  submitLabel?: string;
};

export function SearchBar({
  city,
  disabled = false,
  inputLabel = "Tên thành phố",
  onSearch,
  placeholder = "Nhập thành phố",
  resetKey,
  submitLabel = "Tìm thành phố",
}: SearchBarProps) {
  const [value, setValue] = useState(city);

  useEffect(() => {
    setValue(city);
  }, [city, resetKey]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSearch(value);
  }

  return (
    <form className="search-bar" onSubmit={handleSubmit}>
      <button className="icon-button" type="submit" disabled={disabled} aria-label={submitLabel}>
        <Search size={24} />
      </button>
      <input
        aria-label={inputLabel}
        disabled={disabled}
        placeholder={placeholder}
        value={value}
        onKeyDown={(event) => {
          if (event.key === "Enter") {
            event.preventDefault();
            onSearch(value);
          }
        }}
        onChange={(event) => setValue(event.currentTarget.value)}
        onInput={(event) => setValue(event.currentTarget.value)}
      />
    </form>
  );
}
