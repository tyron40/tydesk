package com.zdesk.companion;
import org.junit.Test;
import static org.junit.Assert.*;
import java.nio.*;
import java.util.*;
import java.util.concurrent.atomic.AtomicLong;
public class AudioPacketsTest {
 byte[] packet(int value){byte[] b=new byte[48];ByteBuffer v=ByteBuffer.wrap(b).order(ByteOrder.LITTLE_ENDIAN);v.putInt(4,40);v.putInt(40,4);v.putInt(44,value);return b;}
 @Test public void slowUploadKeepsEveryQueuedSampleInOrder() throws Exception {
  AudioPackets queue=new AudioPackets();for(int i=1;i<=5;i++)queue.offer(packet(i));
  byte[] batch=queue.pollBatch(0);ByteBuffer b=ByteBuffer.wrap(batch).order(ByteOrder.LITTLE_ENDIAN);
  assertEquals(20,b.getInt(40));for(int i=1;i<=5;i++)assertEquals(i,b.getInt(44+(i-1)*4));assertNull(queue.pollBatch(0));
 }
 @Test public void queueRemainsBoundedAndClearRevokesPendingAudio() throws Exception {
  AudioPackets queue=new AudioPackets();for(int i=1;i<=20;i++)queue.offer(packet(i));
  assertEquals(6,ByteBuffer.wrap(queue.pollBatch(0)).order(ByteOrder.LITTLE_ENDIAN).getInt(44));queue.clear();assertNull(queue.pollBatch(0));
 }
 @Test public void staleSoundIsNotReplayedAfterConnectionOutage() throws Exception {
  AtomicLong time=new AtomicLong();AudioPackets queue=new AudioPackets(time::get);queue.offer(packet(1));time.set(4000000000L);assertNull(queue.pollBatch(0));queue.offer(packet(2));assertNotNull(queue.pollBatch(0));
 }
 @Test(expected=IllegalArgumentException.class) public void oversizedBatchIsRejected(){AudioPackets.merge(Arrays.asList(new byte[192048]));}
}
