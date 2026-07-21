from dataclass import dataclass

@dataclass 
class FusionThresholds:
    #occlusion reasoning thresholds
    occlusion_distance_threshold: float = 0.1
    occlusion_dark_ratio_threshold: float = 0.5
    occlusion_contrast_threshold: float = 20.0
    occlusion_variance_threshold: float = 1000.0
    occlusion_entropy_threshold: float = 3.0
    occlusion_mean_threshold: float = 50.0


    #grasping task reasoning thresholds
    force_contact_threshold: float = 5.0
    tactile_contact_threshold: float = 0.5