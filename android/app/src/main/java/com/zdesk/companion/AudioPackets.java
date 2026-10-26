package com.zdesk.companion;
import java.nio.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.function.LongSupplier;

/** Short, ordered live-audio queue. Never stores files or unbounded history. */
final class AudioPackets {
 private static final class Chunk {final long time;final byte[] wav;Chunk(long time,byte[] wav){this.time=time;this.wav=wav;}}
 private final ArrayBlockingQueue<Chunk> queue=new ArrayBlockingQueue<>(15);
 private final LongSupplier clock;
 AudioPackets(){this(System::nanoTime);}
 AudioPackets(LongSupplier clock){this.clock=clock;}
 void offer(byte[] wav){Chunk c=new Chunk(clock.getAsLong(),wav);if(!queue.offer(c)){queue.poll();queue.offer(c);}}
 void clear(){queue.clear();}
 byte[] pollBatch(long timeoutMs) throws InterruptedException {
  Chunk first=queue.poll(timeoutMs,TimeUnit.MILLISECONDS);if(first==null)return null;
  List<Chunk> entries=new ArrayList<>();entries.add(first);queue.drainTo(entries,4);
  List<byte[]> fresh=new ArrayList<>();long now=clock.getAsLong();
  for(Chunk chunk:entries)if(now-chunk.time<=3000000000L)fresh.add(chunk.wav);
  return fresh.isEmpty()?null:merge(fresh);
 }
 static byte[] merge(List<byte[]> chunks){
  int size=0;for(byte[] wav:chunks){if(wav.length<48||(wav.length-44)%4!=0)throw new IllegalArgumentException("Invalid audio packet");size+=wav.length-44;}
  if(size<=0||size>192000)throw new IllegalArgumentException("Audio batch exceeds two seconds");
  byte[] joined=new byte[44+size];System.arraycopy(chunks.get(0),0,joined,0,44);
  ByteBuffer header=ByteBuffer.wrap(joined).order(ByteOrder.LITTLE_ENDIAN);header.putInt(4,36+size);header.putInt(40,size);
  int offset=44;for(byte[] wav:chunks){System.arraycopy(wav,44,joined,offset,wav.length-44);offset+=wav.length-44;}
  return joined;
 }
}
