from .models import ForceFeatures, ForceScalarData, ForceArrayData, ForceWindow
import numpy as np


class ForceFeatureExtractor:
    def compute(self, window):
        mean = self._per_axis_scalar(window, np.mean)
        rms = self._per_axis_scalar(window, lambda x: np.sqrt(np.mean(x**2)))
        variance = self._per_axis_scalar(window, np.var)
        derivative = self._per_axis_array(window, np.gradient)
        
        jitter = np.std(self.delta_t(window.timestamps))
        frequency = self.frequency()
        timeout = np.mean(self.delta_t(window.timestamps))
        
        force_magnitude = np.mean(np.sqrt(window.fx**2 + window.fy**2 + window.fz**2))
        torque_magnitude = np.mean(np.sqrt(window.tx**2 + window.ty**2 + window.tz**2))
        
        fft = self._per_axis_array(window, np.fft.rfft)
        power_spectrum = self._per_axis_array(fft, lambda x: np.abs(x)**2) #stores total power spectrum for each channel

        high_freq_ratio = self.high_freq_ratio(window, fft, power_spectrum)
        frequency_entropy = self.frequency_entropy(window, fft, power_spectrum)

        return ForceFeatures(
            mean=mean,
            rms=rms,
            variance=variance,
            derivative=derivative,
            jitter=jitter,
            frequency=frequency,
            timeout=timeout,
            force_magnitude=force_magnitude,
            torque_magnitude=torque_magnitude,
            high_freq_ratio=high_freq_ratio,
            frequency_entropy=frequency_entropy
        )
    
    def _per_axis_scalar(self, window: ForceWindow, func):
        return ForceScalarData(
            fx=float(func(window.fx)),
            fy=float(func(window.fy)),
            fz=float(func(window.fz)),
            tx=float(func(window.tx)),
            ty=float(func(window.ty)),
            tz=float(func(window.tz)),
        )
    
    def _per_axis_array(self, window: ForceWindow, func):
        return ForceArrayData(
            fx=func(window.fx),
            fy=func(window.fy),
            fz=func(window.fz),
            tx=func(window.tx),
            ty=func(window.ty),
            tz=func(window.tz)
        )

    def frequency(self, window: ForceWindow):
        expected_frequency = 100.0  # Hz
        actual_frequency = 1.0 / np.mean(self.delta_t(window.timestamps))

    def delta_t(self, timestamps):
        #calculate Δt(i) = t(i) - t(i-1)
        delta_t = np.diff(timestamps)
        return delta_t
    
    def high_freq_ratio(self, window:ForceWindow, fft, power_spectrum):
        #calculate the ratio of high frequency components to low frequency components
        #assuming the first half of the FFT corresponds to low frequencies and the second half to high frequencies
        freq = np.fft.rfftfreq(
            len(window.fx),
            d=np.mean(self.delta_t(window.timestamps))
        )
        freq_cutoff = 10.0  # Hz, this is an arbitrary cutoff for high frequency components


        high_freq_mask = freq > freq_cutoff
        high_freq_power = self._per_axis_array(fft[high_freq_mask], lambda x: np.abs(x)**2)
        high_freq_energy = self._per_axis_array(high_freq_power, np.sum)
        high_freq_ratio = self._per_axis_array(high_freq_energy, lambda x: x / np.sum(power_spectrum))
        return high_freq_ratio
    
    def frequency_entropy(self, window: ForceWindow, fft, power_spectrum):
        #calculate the entropy of the frequency distribution
        prob_distribution = self._per_axis_array(power_spectrum, lambda x: x / np.sum(x))
        entropy = self._per_axis_array(prob_distribution, lambda p: -np.sum(p * np.log2(p + 1e-12)))  # add small value to avoid log(0)
        return entropy