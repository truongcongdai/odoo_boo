import React, { useEffect, useState } from "react";
import { List, Box, Page, Icon } from "zmp-ui";
import { useRecoilValue } from "recoil";
import { displayNameState, userState } from "../state";
import axios from "axios";

const SPointExchangeHistory = () => {
  const { userInfo: user } = useRecoilValue(userState);
  const { Item } = List;
  const [dataSource, setDataSource] = useState([]);
  const baseUrl =
    "https://f095-2001-ee0-4a48-dcd0-6d40-7ac9-9220-b845.ngrok-free.app";

  useEffect(() => {
    const fetchData = async () => {
      if (!user || !user.id) {
        console.error("User or user ID not available");
        return;
      }
      const uid = user.id;
      const response = await axios.post(
        "/zalo_mini_app/point_exchange_history",
        { uid: uid },
        {
          baseURL: baseUrl,
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
          },
        }
      );
      setDataSource(response.data); // Set dataSource to the response data
    };

    fetchData();
  }, []);

  const renderItem = (item) => {
    return (
      <Item
        className="SPointExchangeHistory"
        title={
          <div>
            {item.content}
            <strong>{item.name_pos}</strong>
            <br />
            {item.date_and_code_order}
          </div>
        }
        prefix={
          <Box
            mr={1}
            style={{
              width: "45px",
              height: "45px",
              overflow: "hidden",
            }}
          >
            <img
              style={{ width: "100%", height: "100%" }}
              src="../src/static/icons/logo_boo.png"
            />
          </Box>
        }
        suffix={
          <Box
            mr={1}
            style={{
              width: "50px",
              height: "100%",
              wordBreak: "break-all",
              overflow: "hidden",
              display: "flex",
              alignItems: "center",
            }}
          >
            <p
              style={{
                color:
                  parseInt(item.diem_cong.replace(/,/g, "")) < 0
                    ? "red"
                    : "green",
              }}
            >
              {item.diem_cong}
            </p>
          </Box>
        }
      />
    );
  };

  return (
    <Page className="SPointExchangeHistory">
      <div className="title_history_point">
        <h3>Lịch sử đổi điểm</h3>
      </div>
      <Box m={0} p={0} mt={4}>
        <div className="section-container">
          <List>{dataSource.map(renderItem)}</List>
        </div>
      </Box>
    </Page>
  );
};

export default SPointExchangeHistory;
