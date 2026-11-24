/**
 * Copyright 2025 Beijing Volcano Engine Technology Co., Ltd. All Rights Reserved.
 * SPDX-license-identifier: BSD-3-Clause
 */

// 主区域页面控制器：未加入房间时显示前厅，加入后显示通话页面
import { useSelector } from 'react-redux';
import Antechamber from './Antechamber';
import Room from './Room';

function MainArea() {  // 主内容区域：根据是否加入房间，显示通话页面或通话前页面
  const room = useSelector((state: any) => state.room);     // 从 Redux 获取房间状态
  const isJoined = room.isJoined;       // 判断用户是否已经加入房间
  return isJoined ? <Room /> : <Antechamber />;   // 已加入显示通话页面，未加入显示通话前页面
}

export default MainArea;    
