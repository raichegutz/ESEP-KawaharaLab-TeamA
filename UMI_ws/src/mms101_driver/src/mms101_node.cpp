/**
 * MMS101 Force Sensor Driver for ROS 2
 * Based on ForceSensor Controller Communication Specification Rev.5
 */

#include <rclcpp/rclcpp.hpp>
#include <geometry_msgs/msg/wrench_stamped.hpp>
#include <fcntl.h>
#include <termios.h>
#include <unistd.h>
#include <iostream>
#include <vector>
#include <cstring>
#include <thread>
#include <atomic>

class MMS101Node : public rclcpp::Node
{
public:
  MMS101Node() : Node("mms101_driver")
  {
    // パラメータ設定
    this->declare_parameter("port", "/dev/ttyUSB1");
    this->declare_parameter("frame_id", "sensor_link");
    // 注: 24bitデータを物理量(N, Nm)に変換する係数はセンサ個体や型番によるため
    // ここでは仮の値(1.0)としています。評価ソフトの値と比較して調整が必要です。
    this->declare_parameter("force_scale", 0.001); 
    this->declare_parameter("torque_scale", 0.00001);

    port_name_ = this->get_parameter("port").as_string();
    frame_id_ = this->get_parameter("frame_id").as_string();
    force_scale_ = this->get_parameter("force_scale").as_double();
    torque_scale_ = this->get_parameter("torque_scale").as_double();

    publisher_ = this->create_publisher<geometry_msgs::msg::WrenchStamped>("force_torque", 10);

    ////////////////////////////////////////////////////////////
    /*
    if (open_serial_port()) {
      if (initialize_sensor()) {
        RCLCPP_INFO(this->get_logger(), "Sensor initialized successfully. Starting loop.");
        // 10ms間隔 (100Hz) でデータを取得しにいくタイマー
        
        ///////////////////////////////////////////////////////////////////
        
        timer_ = this->create_wall_timer(
          std::chrono::milliseconds(10), std::bind(&MMS101Node::read_data_callback, this));
        
        serial_thread_ = std::thread(&MMS101Node::serial_loop, this);
      } else {
        RCLCPP_ERROR(this->get_logger(), "Failed to initialize sensor.");
      }
    }
    */
    serial_thread_ = std::thread(&MMS101Node::serial_loop, this);

  }

  ~MMS101Node() {
    /////////////////////////////////////////////////////////////////////////
    /*
    stop_measurement();
    if (serial_fd_ != -1) close(serial_fd_);
    */
    running_ = false;

    if (serial_thread_.joinable())
        serial_thread_.join();

    stop_measurement();

    if (serial_fd_ != -1)
        close(serial_fd_);
  }

private:
  int serial_fd_ = -1;
  std::string port_name_;
  std::string frame_id_;
  double force_scale_;
  double torque_scale_;
  rclcpp::Publisher<geometry_msgs::msg::WrenchStamped>::SharedPtr publisher_;
  //////////////////////////////////////////////rclcpp::TimerBase::SharedPtr timer_;
  std::vector<uint8_t> rx_buffer_;

  //////////////////////
  std::thread serial_thread_;
  std::atomic<bool> running_{true};

  // シリアルポートを開く [cite: 30]
  // Baudrate: 1,000,000 bps, 8bit, No parity, 1 stop bit
  bool open_serial_port()
  {
    serial_fd_ = open(port_name_.c_str(), O_RDWR | O_NOCTTY | O_SYNC);
    if (serial_fd_ < 0) {
      RCLCPP_ERROR(this->get_logger(), "Error opening %s: %s", port_name_.c_str(), strerror(errno));
      return false;
    }

    struct termios tty;
    if (tcgetattr(serial_fd_, &tty) != 0) return false;

    cfsetospeed(&tty, B1000000); // 1Mbps [cite: 30]
    cfsetispeed(&tty, B1000000);

    tty.c_cflag = (tty.c_cflag & ~CSIZE) | CS8; // 8-bit chars
    tty.c_iflag &= ~IGNBRK; // disable break processing
    tty.c_lflag = 0; // no signaling chars, no echo, no canonical processing
    tty.c_oflag = 0; // no remapping, no delays
    //////////////////////////////////////////////////
    /*
    tty.c_cc[VMIN]  = 0; // read doesn't block
    tty.c_cc[VTIME] = 1; // 0.1 seconds read timeout
    */
    tty.c_cc[VMIN]  = 25; // read doesn't block
    tty.c_cc[VTIME] = 0; // 0.1 seconds read timeout

    tty.c_iflag &= ~(IXON | IXOFF | IXANY); // shut off xon/xoff ctrl
    tty.c_cflag |= (CLOCAL | CREAD); // ignore modem controls, enable reading
    tty.c_cflag &= ~(PARENB | PARODD); // shut off parity [cite: 30]
    tty.c_cflag &= ~CSTOPB; // 1 stop bit [cite: 30]
    tty.c_cflag &= ~CRTSCTS; // no hardware flow control [cite: 30]

    if (tcsetattr(serial_fd_, TCSANOW, &tty) != 0) return false;
    return true;
  }

  void send_command(const std::vector<uint8_t>& cmd) {
    ssize_t bytes_written= write(serial_fd_, cmd.data(), cmd.size());
    
    if (bytes_written < 0) {
      RCLCPP_ERROR(this->get_logger(), "Error writing to serial port: %s", strerror(errno));
    }
    else if(static_cast<size_t>(bytes_written) != cmd.size()) {
      RCLCPP_ERROR(this->get_logger(), "Incomplete write to serial port. Expected %zu bytes, wrote %zd bytes.", cmd.size(), bytes_written);
    }

    // 少し待機（コマンド処理時間）
    std::this_thread::sleep_for(std::chrono::milliseconds(2));
  }

  // 応答読み捨て用（設定コマンド等のレスポンス）
 // Read and validate a command response
  bool flush_response(const std::string &command_name){
      uint8_t buf[64];
      ssize_t n = read(serial_fd_, buf, sizeof(buf));

      if (n < 0){
          RCLCPP_ERROR(this->get_logger(), "%s: Serial read failed.", command_name.c_str());
          return false;
      }

      if (n == 0){
          RCLCPP_ERROR(this->get_logger(),"%s: No response received.",command_name.c_str());
          return false;
      }

      if (buf[0] != 0x00){
          RCLCPP_ERROR(this->get_logger(),"%s: Sensor returned error status 0x%02X (read %zd bytes).",command_name.c_str(),buf[0],n);
          return false;
      }

      RCLCPP_INFO(this->get_logger(),"%s: OK (read %zd bytes).",command_name.c_str(),n);
      return true;
  }

  // 初期化シーケンス 
  bool initialize_sensor()
  {
    RCLCPP_INFO(this->get_logger(), "Initializing MMS101...");

    // 1. Board Select (ID=0x00) [cite: 90]
    // Cmd: 54 02 10 00
    send_command({0x54, 0x02, 0x10, 0x00});
    if(!flush_response("Board Select")) {
      return false;
    }

    // 2. Power Switch (VDD12 ON) [cite: 128]
    // Cmd: 54 03 36 00 01
    send_command({0x54, 0x03, 0x36, 0x00, 0x01});
    if(!flush_response("Power Switch (VDD12 ON)")) {
      return false;
    }
    std::this_thread::sleep_for(std::chrono::milliseconds(10));

    // 2. Power Switch (VDD45 ON) [cite: 128]
    // Cmd: 54 03 36 05 01 (LDO ID 0x05 for VDD45)
    send_command({0x54, 0x03, 0x36, 0x05, 0x01});
    if(!flush_response("Power Switch (VDD45 ON)")) {
      return false;
    }
    std::this_thread::sleep_for(std::chrono::milliseconds(10));

    // 3. Axis Select & Idle Loop [cite: 310, 161]
    // 軸ごとにSelectしてIdleにする必要がある
    for (uint8_t axis = 0; axis < 6; axis++) {
      // Axis Select [cite: 145]
      // Cmd: 54 02 1C [axis]
      send_command({0x54, 0x02, 0x1C, axis});
      if(!flush_response("Axis Select")) {
        return false;
      }

      // Idle Command [cite: 169]
      // Cmd: 53 02 57 94 (Instruction Code is 0x53)
      send_command({0x53, 0x02, 0x57, 0x94});
      if(!flush_response("Idle Command")) {
        return false;
      }

      // Idle状態になるまで10msec待つ [cite: 162]
      std::this_thread::sleep_for(std::chrono::milliseconds(15));
    }

    // 4. Bootload (マトリクス係数読み出し) [cite: 182]
    // Cmd: 54 01 B0
    send_command({0x54, 0x01, 0xB0});
    if(!flush_response("Bootload")) {
      return false;
    }
    std::this_thread::sleep_for(std::chrono::milliseconds(50));

    // Interval Measureコマンド
    send_command({0x54, 0x04, 0x43, 0x00, 0x27, 0x10}); // 10ms間隔
    if(!flush_response("Interval Measure")) {
      return false;
    }

    // 5. Start (測定開始) [cite: 283]
    // Cmd: 54 02 23 00
    send_command({0x54, 0x02, 0x23, 0x00});
    
    // 初回のレスポンスはStatusのみなので読み捨てる [cite: 273]
    std::this_thread::sleep_for(std::chrono::milliseconds(10));
    if(!flush_response("Start")) {
      return false;
    }

    return true;
  }

  void stop_measurement() {
    // Stop Command [cite: 304]
    // Cmd: 54 01 33
    send_command({0x54, 0x01, 0x33});
  }

  // 24bit Big Endian 符号付きデータを int32_t に変換 [cite: 288, 289]
  int32_t parse_24bit_be(const uint8_t* data) {
    int32_t val = (data[0] << 16) | (data[1] << 8) | data[2];
    // 符号拡張 (24bit目のビットが立っていたら上位を1で埋める)
    if (val & 0x800000) {
      val |= 0xFF000000;
    }
    return val;
  }



  ////////////////////////////////////////////////////////////////////////
  void serial_loop()
  {
    while (rclcpp::ok() && running_)
    {
        /////////////////////////////////////////////////////////////////
        // Open serial port
        /////////////////////////////////////////////////////////////////

        if (!open_serial_port())
        {
            RCLCPP_WARN(
                this->get_logger(),
                "Waiting for sensor on %s...",
                port_name_.c_str());

            std::this_thread::sleep_for(std::chrono::seconds(1));
            continue;
        }

        /////////////////////////////////////////////////////////////////
        // Initialize sensor
        /////////////////////////////////////////////////////////////////

        if (!initialize_sensor())
        {
            close(serial_fd_);
            serial_fd_ = -1;

            std::this_thread::sleep_for(std::chrono::seconds(1));
            continue;
        }

        RCLCPP_INFO(this->get_logger(), "Sensor initialized successfully. Starting loop.");
        /////////////////////////////////////////////////////////////////
        // Read until disconnected
        /////////////////////////////////////////////////////////////////

        while (rclcpp::ok() && running_)
        {
            if (!read_data_callback())
            {
                break;
            }
        }

        /////////////////////////////////////////////////////////////////
        // Cleanup after disconnect
        /////////////////////////////////////////////////////////////////

        stop_measurement();

        close(serial_fd_);
        serial_fd_ = -1;

        RCLCPP_WARN(this->get_logger(), "Sensor disconnected.");
    }
  }


  bool read_data_callback()
  {
    // レスポンスフォーマット (25 bytes) [cite: 276]
    // Byte 0: Status
    // Byte 1: Length (0x17 = 23 bytes payload)
    // Byte 2: 0x80
    // Byte 3: 0x00
    // Byte 4-6: Fx
    // Byte 7-9: Fy
    // Byte 10-12: Fz
    // Byte 13-15: Mx
    // Byte 16-18: My
    // Byte 19-21: Mz
    // Byte 22-24: Time
    
    /*
    uint8_t buf[25];
    int n = read(serial_fd_, buf, 25);
    

    if (n == 25) {
        // Status Check (0x00 is OK) [cite: 76]
        if (buf[0] != 0x00) return;

        int32_t raw_fx = parse_24bit_be(&buf[4]);
        int32_t raw_fy = parse_24bit_be(&buf[7]);
        int32_t raw_fz = parse_24bit_be(&buf[10]);
        int32_t raw_mx = parse_24bit_be(&buf[13]);
        int32_t raw_my = parse_24bit_be(&buf[16]);
        int32_t raw_mz = parse_24bit_be(&buf[19]);

        auto msg = geometry_msgs::msg::WrenchStamped();
        msg.header.stamp = this->now();
        msg.header.frame_id = frame_id_;

        // 変換 (単位合わせが必要)
        msg.wrench.force.x = raw_fx * force_scale_;
        msg.wrench.force.y = raw_fy * force_scale_;
        msg.wrench.force.z = raw_fz * force_scale_;
        msg.wrench.torque.x = raw_mx * torque_scale_;
        msg.wrench.torque.y = raw_my * torque_scale_;
        msg.wrench.torque.z = raw_mz * torque_scale_;

        publisher_->publish(msg);
    }
    */

    uint8_t temp[128];
    
    /////////////////////////////////////////////////////////////////////////
    /*
    int n = read(serial_fd_, temp, sizeof(temp));

    if (n < 0) {
        RCLCPP_ERROR(this->get_logger(), "Error reading from serial port: %s", strerror(errno));
        return;
    }
    */

    int n = read(serial_fd_, temp, sizeof(temp));
    rclcpp::Time rx_stamp = this->get_clock()->now();

    if (n < 0)
    {
      if (errno == ENOENT)
      {
          // Device not present yet.
          return false;
      }

      RCLCPP_ERROR(
          this->get_logger(),
          "Error opening %s: %s",
          port_name_.c_str(),
          strerror(errno));

      return false;
    }

    if (n > 0){
        rx_buffer_.insert(rx_buffer_.end(), temp, temp + n);
    }

    size_t start = 0;
    //check for validity bytes 00 17 80 00
    while (start + 25 <= rx_buffer_.size()) {
        // Status Check (0x00 is OK) [cite: 76]
        if (rx_buffer_[start] != 0x00){
          start++;
          continue;
        };

        if (rx_buffer_[start] == 0x00 && rx_buffer_[start + 1] == 0x17 && rx_buffer_[start + 2] == 0x80 && rx_buffer_[start + 3] == 0x00) {
            //valid data packet
            int32_t raw_fx = parse_24bit_be(&rx_buffer_[start + 4]);
            int32_t raw_fy = parse_24bit_be(&rx_buffer_[start + 7]);
            int32_t raw_fz = parse_24bit_be(&rx_buffer_[start + 10]);
            int32_t raw_mx = parse_24bit_be(&rx_buffer_[start + 13]);
            int32_t raw_my = parse_24bit_be(&rx_buffer_[start + 16]);
            int32_t raw_mz = parse_24bit_be(&rx_buffer_[start + 19]); 

            auto msg = geometry_msgs::msg::WrenchStamped();
            msg.header.stamp = rx_stamp;
            msg.header.frame_id = frame_id_;

            msg.wrench.force.x = raw_fx * force_scale_;
            msg.wrench.force.y = raw_fy * force_scale_;
            msg.wrench.force.z = raw_fz * force_scale_;
            msg.wrench.torque.x = raw_mx * torque_scale_;
            msg.wrench.torque.y = raw_my * torque_scale_;
            msg.wrench.torque.z = raw_mz * torque_scale_;

            publisher_->publish(msg);

            start+=25;
        }
        else{
            //invalid data packet, discard first byte
            start++;
        }
      }
      //clear the buffer of the processed packet
      rx_buffer_.erase(rx_buffer_.begin(),rx_buffer_.begin() + start);

      return true;
  }
};

int main(int argc, char **argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<MMS101Node>());
  rclcpp::shutdown();
  return 0;
}