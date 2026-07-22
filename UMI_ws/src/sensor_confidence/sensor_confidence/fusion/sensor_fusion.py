import numpy as np

from sensor_confidence.common.task_phase import TaskPhase
from .models import FusionThresholds

class SensorFusion:
    def __init__(self, logger):
        self.thresholds = FusionThresholds()
        self._logger = logger

    def fuse_confidences(self,
        left_force_health,
        right_force_health,
        left_force_features,
        right_force_features,

        vision_health,
        vision_features,

        left_tactile_health,
        right_tactile_health,
        left_tactile_features,
        right_tactile_features,

        task_phase,
        ToF_features,
    ):
        missing = []
        if left_force_health is None:
            missing.append("left force")
        if right_force_health is None:
            missing.append("right force")
        if vision_health is None:
            missing.append("vision")
        if left_tactile_health is None:
            missing.append("left tactile")
        if right_tactile_health is None:
            missing.append("right tactile")
        if missing:
            self._logger.warn(
            "Fusion waiting for: " + ", ".join(missing),
            throttle_duration_sec=5.0
        )
            return None
        
        #initialize adjustments for each sensor type before fusion
        force_left_adj=0.0
        force_right_adj=0.0
        vision_adj=0.0
        tactile_left_adj=0.0
        tactile_right_adj=0.0
        
        #fuse confidence values from each sensor type to calculate final confidence
        vision_adj = self.occlusion_reasoning(task_phase, vision_features, ToF_features, left_force_features, right_force_features, left_tactile_features, right_tactile_features)
        force_left_adj, force_right_adj, tactile_left_adj, tactile_right_adj, vision_adj = self.task_reasoning(task_phase, left_force_features, right_force_features, left_tactile_features, right_tactile_features, vision_health)

        force_left_confidence = np.clip(
            left_force_health.confidence + force_left_adj,
            0.0,
            1.0
        )

        force_right_confidence = np.clip(
            right_force_health.confidence + force_right_adj,
            0.0,
            1.0
        )

        vision_confidence = np.clip(
            vision_health.confidence + vision_adj,
            0.0,
            1.0
        )

        tactile_left_confidence = np.clip(
            left_tactile_health.confidence + tactile_left_adj,
            0.0,
            1.0
        )

        tactile_right_confidence = np.clip(
            right_tactile_health.confidence + tactile_right_adj,
            0.0,
            1.0
        )

        return force_left_confidence, force_right_confidence, vision_confidence, tactile_left_confidence, tactile_right_confidence
    
    def occlusion_reasoning(self,task,vision_features,tof_features,left_force_features,right_force_features,left_tactile_features,right_tactile_features):
        """
        Returns an adjustment to the vision confidence.
        Negative adjustment -> likely camera occlusion.
        """

        if tof_features is None:
            return 0.0

        t = self.thresholds
        score = 0

        # ----------------------------------------------------
        # ToF evidence
        # ----------------------------------------------------
        if tof_features.mean_distance < t.occlusion_distance_threshold:
            score += 2

        # ----------------------------------------------------
        # Vision evidence
        # ----------------------------------------------------
        if np.mean(vision_features.dark_pixel_ratio) > t.occlusion_dark_ratio_threshold:
            score += 1

        if np.mean(vision_features.contrast) < t.occlusion_contrast_threshold:
            score += 1

        if np.mean(vision_features.variance) < t.occlusion_variance_threshold:
            score += 1

        if np.mean(vision_features.spatial_entropy) < t.occlusion_entropy_threshold:
            score += 1

        if np.mean(vision_features.mean) < t.occlusion_mean_threshold:
            score += 1

        # ----------------------------------------------------
        # Was contact actually detected?
        # ----------------------------------------------------

        force_contact = (
            left_force_features.force_magnitude > t.force_contact_threshold or
            right_force_features.force_magnitude > t.force_contact_threshold
        )

        tactile_contact = (
            np.mean(left_tactile_features.variance) > t.tactile_contact_threshold or
            np.mean(right_tactile_features.variance) > t.tactile_contact_threshold
        )

        # ----------------------------------------------------
        # Context reasoning
        # ----------------------------------------------------

        if task == TaskPhase.GRASPING:

            # Close object + contact is expected.
            if force_contact or tactile_contact:
                score -= 2

        # ----------------------------------------------------
        # Final decision
        # ----------------------------------------------------

        if score >= 6:
            return -0.35

        elif score >= 4:
            return -0.20

        else:
            return 0.0
        
    
    def task_reasoning(self,task,left_force_features,right_force_features,left_tactile_features,right_tactile_features,vision_health):
        """
        Adjusts the confidence of each sensor type based on the current task phase.
        """
        t = self.thresholds
        force_left_adj = 0.0
        force_right_adj = 0.0
        tactile_left_adj = 0.0
        tactile_right_adj = 0.0
        vision_adj = 0.0

        force_contact = self.force_contact_detector(left_force_features, right_force_features)
        tactile_contact = self.tactile_contact_detector(left_tactile_features, right_tactile_features)

        if task == TaskPhase.IDLE or task == TaskPhase.APPROACH or task == TaskPhase.RELEASE:
            # During idle, we expect no contact to be detected by force and tactile sensors.
            if force_contact:
                force_left_adj -= 0.4
                force_right_adj -= 0.4

            if tactile_contact:
                tactile_left_adj -= 0.4
                tactile_right_adj -= 0.4
        elif task == TaskPhase.GRASP or task == TaskPhase.LIFT:
            # During grasping, we expect contact to be detected by force and tactile sensors.
            if not force_contact:
                force_left_adj -= 0.4
                force_right_adj -= 0.4

            if not tactile_contact:
                tactile_left_adj -= 0.4
                tactile_right_adj -= 0.4
            
            # Vision scene becomes more complex during grasping.
            # Reduce penalties that are influenced by scene content.
            vision_adj += (
                vision_health.penalties.variance * 0.75 +
                vision_health.penalties.contrast * 0.75 +
                vision_health.penalties.entropy * 0.75
            )

        return force_left_adj, force_right_adj, tactile_left_adj, tactile_right_adj, vision_adj


    def tactile_contact_detector(self, left_tactile, right_tactile):
        """
        Returns True if either GelSight sensor appears to be in contact.
        """

        t = self.thresholds

        score = 0

        # ---------- Variance ----------
        if (
            np.mean(left_tactile.variance) > t.tactile_variance_contact_threshold or
            np.mean(right_tactile.variance) > t.tactile_variance_contact_threshold
        ):
            score += 1

        # ---------- Contrast ----------
        if (
            np.mean(left_tactile.contrast) > t.tactile_contrast_contact_threshold or
            np.mean(right_tactile.contrast) > t.tactile_contrast_contact_threshold
        ):
            score += 1

        # ---------- Entropy ----------
        if (
            np.mean(left_tactile.spatial_entropy) > t.tactile_entropy_contact_threshold or
            np.mean(right_tactile.spatial_entropy) > t.tactile_entropy_contact_threshold
        ):
            score += 1

        # ---------- Difference from reference ----------
        if (
            np.mean(left_tactile.reference_SD) > t.reference_sd_contact_threshold or
            np.mean(right_tactile.reference_SD) > t.reference_sd_contact_threshold
        ):
            score += 1

        if (
            np.mean(left_tactile.reference_mean) > t.reference_mean_contact_threshold or
            np.mean(right_tactile.reference_mean) > t.reference_mean_contact_threshold
        ):
            score += 1

        return score >= 3
    
    def force_contact_detector(self, left_force, right_force):
        """
        Returns True if the force sensors indicate physical contact.
        """

        t = self.thresholds

        score = 0

        # ---------- Force magnitude ----------
        if (left_force.force_magnitude > t.force_contact_threshold or
            right_force.force_magnitude > t.force_contact_threshold):
            score += 2

        # ---------- Torque magnitude ----------
        if (left_force.torque_magnitude > t.torque_contact_threshold or
            right_force.torque_magnitude > t.torque_contact_threshold):
            score += 1

        # ---------- RMS ----------
        if (
            np.mean([
                left_force.rms.fx,
                left_force.rms.fy,
                left_force.rms.fz,
                right_force.rms.fx,
                right_force.rms.fy,
                right_force.rms.fz
            ]) > t.rms_contact_threshold
        ):
            score += 1

        # ---------- Variance ----------
        if (
            np.mean([
                left_force.variance.fx,
                left_force.variance.fy,
                left_force.variance.fz,
                right_force.variance.fx,
                right_force.variance.fy,
                right_force.variance.fz
            ]) > t.variance_contact_threshold
        ):
            score += 1

        # ---------- Sensor looks healthy ----------
        if (
            left_force.high_freq_ratio < t.high_freq_contact_threshold and
            right_force.high_freq_ratio < t.high_freq_contact_threshold
        ):
            score += 1

        return score >= 4
    
