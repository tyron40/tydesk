package com.zdesk.companion;
import org.junit.Test;
import static org.junit.Assert.*;
import java.nio.*;
public class ProtocolTest {
 @Test public void httpsOriginValidation(){new Api("https://example.com",null);for(String value:new String[]{"http://example.com","https://user:secret@example.com","https://example.com/path","https://example.com?q=secret"}){try{new Api(value,null);fail("Unsafe origin accepted");}catch(IllegalArgumentException expected){}}}
 @Test public void safeSelectedFilenames(){assertTrue(ShareService.validName("photo-1.jpg"));for(String value:new String[]{"../secret","CON","file.","file/secret","x.exe:stream"})assertFalse(ShareService.validName(value));}
 @Test public void monoAudioBecomesValidStereoWav(){byte[] bytes=ShareService.wav(new short[]{1000,-1000},2);ByteBuffer b=ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN);assertEquals(52,bytes.length);assertEquals(2,b.getShort(22));assertEquals(24000,b.getInt(24));assertEquals(1000,b.getShort(44));assertEquals(1000,b.getShort(46));assertEquals(-1000,b.getShort(48));}
}
