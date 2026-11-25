"""
Calculator Logic Module
Contains all calculation functions for the 3D printing calculator
"""

import math


class PrintCalculator:
    """
    Core calculation engine for 3D printing estimations
    """

    def calculate_piece_cost(self, price_per_gram, time_minutes, weight_grams,
                            electricity_cost_kwh, printer_power_watts,
                            cost_per_min_machine, failure_percent, profit_margin_percent):
        """
        Calculate the cost per printed piece including materials, electricity, machine cost, failure rate, and profit margin

        Args:
            price_per_gram: Cost of filament per gram ($)
            time_minutes: Print time in minutes
            weight_grams: Filament weight used in grams
            electricity_cost_kwh: Cost of electricity per kWh ($)
            printer_power_watts: Power consumption of printer in watts
            cost_per_min_machine: Cost per minute of machine operation ($)
            failure_percent: Percentage to account for failures (%)
            profit_margin_percent: Desired profit margin (%)

        Returns:
            Dictionary with cost breakdown
        """
        # Material cost
        material_cost = price_per_gram * weight_grams

        # Electricity cost
        # Convert minutes to hours, watts to kilowatts
        time_hours = time_minutes / 60
        power_kw = printer_power_watts / 1000
        electricity_cost = time_hours * power_kw * electricity_cost_kwh

        # Machine operation cost
        machine_cost = time_minutes * cost_per_min_machine

        # Base cost (before failure adjustment)
        base_cost = material_cost + electricity_cost + machine_cost

        # Failure cost (percentage added to account for failed prints)
        failure_cost = base_cost * (failure_percent / 100)

        # Total cost (precio bruto - before profit)
        gross_price = base_cost + failure_cost

        # Calculate profit
        profit = gross_price * (profit_margin_percent / 100)

        # Net price (precio neto - final sale price)
        net_price = gross_price + profit

        return {
            'material_cost': material_cost,
            'electricity_cost': electricity_cost,
            'machine_cost': machine_cost,
            'base_cost': base_cost,
            'failure_cost': failure_cost,
            'gross_price': gross_price,
            'profit': profit,
            'net_price': net_price,
            'time_hours': time_hours
        }

    def convert_material(self, diameter_mm, density_g_cm3, value, conversion_type):
        """
        Convert between filament weight, length, and volume

        Args:
            diameter_mm: Filament diameter in millimeters
            density_g_cm3: Material density in g/cm³
            value: The value to convert from
            conversion_type: Type of conversion ("Peso (g)", "Longitud (m)", "Volumen (cm³)")

        Returns:
            Dictionary with all three measurements
        """
        # Calculate cross-sectional area in cm²
        radius_cm = (diameter_mm / 2) / 10  # Convert mm to cm
        area_cm2 = math.pi * (radius_cm ** 2)

        # Calculate based on input type
        if conversion_type == "Peso (g)":
            weight = value
            volume = weight / density_g_cm3
            length = volume / area_cm2  # in cm
            length_m = length / 100  # Convert to meters

        elif conversion_type == "Longitud (m)":
            length_m = value
            length_cm = length_m * 100
            volume = length_cm * area_cm2
            weight = volume * density_g_cm3

        elif conversion_type == "Volumen (cm³)":
            volume = value
            weight = volume * density_g_cm3
            length_cm = volume / area_cm2
            length_m = length_cm / 100

        else:
            raise ValueError("Invalid conversion type")

        return {
            'weight': weight,
            'length': length_m,
            'volume': volume
        }

    def estimate_print_time(self, layer_height_mm, model_height_mm,
                          print_speed_mm_s, perimeter_length_mm, infill_area_mm2):
        """
        Estimate print time based on layer parameters

        Args:
            layer_height_mm: Height of each layer in mm
            model_height_mm: Total height of model in mm
            print_speed_mm_s: Print speed in mm/s
            perimeter_length_mm: Average perimeter length per layer in mm
            infill_area_mm2: Average infill area per layer in mm²

        Returns:
            Dictionary with time estimation
        """
        # Calculate number of layers
        num_layers = int(model_height_mm / layer_height_mm)

        # Estimate time per layer
        # Time for perimeter
        perimeter_time = perimeter_length_mm / print_speed_mm_s

        # Estimate infill length (assuming 20% infill with 2mm spacing)
        infill_spacing = 2  # mm
        infill_length = infill_area_mm2 / infill_spacing * 0.2  # 20% infill
        infill_time = infill_length / print_speed_mm_s

        # Add some overhead for travel moves (estimate 20% extra)
        time_per_layer = (perimeter_time + infill_time) * 1.2

        # Total time
        total_seconds = time_per_layer * num_layers
        total_minutes = total_seconds / 60
        total_hours = total_minutes / 60

        return {
            'layers': num_layers,
            'time_per_layer': time_per_layer,
            'total_minutes': total_minutes,
            'total_hours': total_hours
        }

    def calculate_scaling(self, original_dimension, original_weight, scale_percent):
        """
        Calculate the effects of scaling a model

        Args:
            original_dimension: Original dimension in mm
            original_weight: Original weight in grams
            scale_percent: Scale percentage (e.g., 150 for 150%)

        Returns:
            Dictionary with scaled values
        """
        # Convert percentage to factor
        scale_factor = scale_percent / 100

        # Linear scaling for dimensions
        new_dimension = original_dimension * scale_factor

        # Cubic scaling for weight/volume
        # Weight increases by the cube of the scale factor
        weight_factor = scale_factor ** 3
        new_weight = original_weight * weight_factor

        # Calculate difference
        weight_difference = new_weight - original_weight

        return {
            'new_dimension': new_dimension,
            'new_weight': new_weight,
            'scale_factor': scale_factor,
            'weight_factor': weight_factor,
            'weight_difference': weight_difference
        }

    def calculate_spool_remaining(self, spool_weight_g, used_weight_g, spool_price):
        """
        Calculate remaining filament on spool and value

        Args:
            spool_weight_g: Total spool weight in grams (usually 1000g)
            used_weight_g: Weight already used in grams
            spool_price: Price paid for the spool

        Returns:
            Dictionary with remaining filament info
        """
        remaining_weight = spool_weight_g - used_weight_g
        remaining_percent = (remaining_weight / spool_weight_g) * 100
        price_per_gram = spool_price / spool_weight_g
        remaining_value = remaining_weight * price_per_gram

        return {
            'remaining_weight': remaining_weight,
            'remaining_percent': remaining_percent,
            'price_per_gram': price_per_gram,
            'remaining_value': remaining_value
        }
    
    def calculate_quote_total(self, pieces, global_extras):
        """
        Calculate the total for a full quote (pieces already include any
        package cost baked into their subtotal, plus one-time quote extras)
        """
        pieces_subtotal = sum(p.get('subtotal', 0) for p in pieces)
        extras_subtotal = sum(global_extras.values()) if global_extras else 0
        total = pieces_subtotal + extras_subtotal

        return {
            'pieces_subtotal': pieces_subtotal,
            'extras_subtotal': extras_subtotal,
            'total': total
        }