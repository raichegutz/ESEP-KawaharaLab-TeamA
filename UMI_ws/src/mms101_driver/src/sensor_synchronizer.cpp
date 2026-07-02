#include <rclcpp/rclcpp.hpp>
#include <geometry_msgs/msg/wrench_stamped.hpp>
#include <message_filters/subscriber.h>
#include <message_filters/synchronizer.h>
#include <message_filters/sync_policies/approximate_time.h>
#include <rmw/qos_profiles.h>

class SensorSynchronizer : public rclcpp::Node
{
    public:
        SensorSynchronizer() : Node("sensor_synchronizer")
        {
            //subscribe to the left and right sensor topics
            left_sensor_sub_.subscribe(this, "/force_torque/left", rmw_qos_profile_sensor_data);
            right_sensor_sub_.subscribe(this, "/force_torque/right", rmw_qos_profile_sensor_data);

            //create publishers for the individual sensor data
            left_sensor_pub_ = this->create_publisher<geometry_msgs::msg::WrenchStamped>("/sync/force_torque/left", 10);
            right_sensor_pub_ = this->create_publisher<geometry_msgs::msg::WrenchStamped>("/sync/force_torque/right", 10);

            //create a synchronizer with an approximate time policy
            sync_ = std::make_unique<message_filters::Synchronizer<SyncPolicy>
            >(
                SyncPolicy(10),
                left_sensor_sub_,
                right_sensor_sub_
            );
            sync_->setMaxIntervalDuration(rclcpp::Duration::from_seconds(0.01));
            sync_->registerCallback(std::bind(&SensorSynchronizer::synchronized_callback, this, std::placeholders::_1, std::placeholders::_2));
        }
    private:
        //only called when both left and right sensor messages are received within a certain time window
        void synchronized_callback(
            const geometry_msgs::msg::WrenchStamped::ConstSharedPtr& left_msg, 
            const geometry_msgs::msg::WrenchStamped::ConstSharedPtr& right_msg)
        {
            //publish both left and right sensor data 
            left_sensor_pub_->publish(*left_msg);
            right_sensor_pub_->publish(*right_msg);
        }

        //synchronizer 
        typedef message_filters::sync_policies::ApproximateTime<
            geometry_msgs::msg::WrenchStamped, 
            geometry_msgs::msg::WrenchStamped
        > SyncPolicy;
        std::unique_ptr<message_filters::Synchronizer<SyncPolicy>> sync_;

        //publishers and subscribers
        message_filters::Subscriber<geometry_msgs::msg::WrenchStamped> left_sensor_sub_;
        message_filters::Subscriber<geometry_msgs::msg::WrenchStamped> right_sensor_sub_;
        rclcpp::Publisher<geometry_msgs::msg::WrenchStamped>::SharedPtr left_sensor_pub_;
        rclcpp::Publisher<geometry_msgs::msg::WrenchStamped>::SharedPtr right_sensor_pub_;
};

int main(int argc, char * argv[])
{
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<SensorSynchronizer>());
    rclcpp::shutdown();
    return 0;
}

