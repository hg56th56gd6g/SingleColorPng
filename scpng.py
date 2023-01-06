#-*- coding:utf-8 -*-
#Single Color png,前6个参数是关于图像信息的,然后4个参数是关于zlib的,倒数第3,2个参数是输出文件和临时文件
#倒数第4个参数是缓冲区大小,越大占用内存越高,速度越快(文件缓冲区(单位字节)和zlib输入缓冲区(单位4字节))
#最后一个参数是(前4字符是"True"代表启用,其他任何值都是禁用)是否使用更高级的ui
#高级ui可能影响性能,可能有bug,True后面跟"<float>",代表轮询时的睡眠时间(单位秒)
#Level:0-9,越大压缩比越大,速度越慢
#WindowBits:9-15,表示窗口大小为2**WindowBits,越大压缩比越大,内存占用越高
#MemLevel:1-9,越大压缩比越大,速度越快,内存占用越高
#Strategy:Z_DEFAULT_STRATEGY,默认压缩策略;Z_FILTERED,更多的huffman编码和更少的string match;Z_HUFFMAN_ONLY,只有huffman编码
#ps:还有两个在后续版本加入的常量;Z_RLE(zlib 1.2.0.1),将匹配距离设为1(游程编码);Z_FIXED(zlib 1.2.2.2),防止使用动态huffman编码
#python scpng.py <R> <G> <B> <A> <Width> <Height> <Level> <WindowBits> <MemLevel> <Strategy(str)> <BufferSize> <OutputFilePath> <TempFilePath> [UI]
if __name__=="__main__":
    from sys import argv
    from struct import pack
    import zlib
    crc32=zlib.crc32
    R=int(argv[1])
    G=int(argv[2])
    B=int(argv[3])
    A=int(argv[4])
    Width=int(argv[5])
    Height=int(argv[6])
    Level=int(argv[7])
    WindowBits=int(argv[8])
    MemLevel=int(argv[9])
    Strategy=getattr(zlib,argv[10],None)
    BufferSize=int(argv[11])
    assert 0<=R<=255 and 0<=G<=255 and 0<=B<=255 and 0<=A<=255,"is not 0<=\"R/G/B/A\"<=255"
    assert 1<=Width<=2147483647 and 1<=Height<=2147483647,"is not 1<=\"Width/Height\"<=2147483647"
    assert 0<=Level<=9,"is not 0<=\"Level\"<=9"
    assert 9<=WindowBits<=15,"is not 9<=\"WindowBits\"<=15"
    assert 1<=MemLevel<=9,"is not 1<=\"MemLevel\"<=9"
    assert 1<=BufferSize,"is not 1<=\"BufferSize\""
    #判断是否用高级ui
    if argv[14][:4:]=="True":
        from threading import Thread
        from time import sleep
        from timeit import default_timer
        from sys import stdout
        stdout=stdout.write
        PrintData=""
        PrintFinish=True
        TimeSleep=float(argv[14][4::])
        TimeStart=default_timer()
        def Print(Data):
            global PrintData,PrintFinish
            while not PrintFinish:
                if not Thread.is_alive():
                    raise Exception("print thread dead")
                sleep(TimeSleep)
            PrintData=Data
            PrintFinish=False
        def MultiThreadingUI():
            global PrintFinish,TimeStart
            Loop=["-","\\","|","/"]
            Stat=0
            while True:
                stdout("%c%s\r"%(Loop[Stat],str(default_timer()-TimeStart)))
                if Stat==3:
                    Stat=0
                else:
                    Stat+=1
                if not PrintFinish:
                    stdout(str(default_timer()-TimeStart))
                    if PrintData=="__stop__":
                        exit()
                    stdout("\n%s\n"%PrintData)
                    PrintFinish=True
                    TimeStart=default_timer()
                sleep(TimeSleep)
        Thread=Thread(target=MultiThreadingUI)
        Thread.start()
    else:
        def Print(Data):
            if Data=="__stop__":
                exit()
            print(Data)
    #打开输出的png文件
    with open(argv[12],"wb",BufferSize) as File:
        Write=File.write
        #png头,数字采用大端编码,uint32范围是0-2147483647,每一块(4字节数据长度,4字节块名称,数据,4字节块名称+数据的crc32效验)
        Write("\x89\x50\x4e\x47\x0d\x0a\x1a\x0a")
        #IHDR(元数据块)
        Write("\x00\x00\x00\x0d" "IHDR")
        #IHDR数据(4字节图像宽度,4字节图像高度,1字节采样深度(8bit),1字节色彩类型(RGBA),1字节压缩方式(deflate),1字节滤波器方式(无),1字节隔行扫描方式(不隔行))
        Buffer=pack("!I",Width)+pack("!I",Height)+"\x08" "\x06" "\x00\x00\x00"
        Write(Buffer)
        #IHDR效验(第二个参数是"IHDR"的crc32值 & 0xffffffff)
        Write(pack("!I",crc32(Buffer,2829168138)&0xffffffff))
        #IDAT(图像数据块,每行像素前加\x00,然后用zlib格式压缩,如果压缩完的数据长度大于2147483647,就要分多块)
        CompressObject=zlib.compressobj(Level,zlib.DEFLATED,WindowBits,MemLevel,Strategy)
        Compress=CompressObject.compress
        #每行分为两部分,Start(\x00+不足一个Loop的部分),Loop(BufferSize个像素,重复Length次)
        Start="\x00"+((chr(R)+chr(G)+chr(B)+chr(A))*(Width%BufferSize))
        Loop=(chr(R)+chr(G)+chr(B)+chr(A))*BufferSize
        Length=Width//BufferSize
        #先将压缩数据全部写入临时文件,然后统一复制到输出文件
        with open(argv[13],"wb+",BufferSize) as Temp:
            TempIO=Temp.write
            del argv,R,G,B,A,Width,Level,WindowBits,MemLevel,Strategy
            Print("==StartCompress")
            while Height:
                Height-=1
                TempIO(Compress(Start))
                TempLength=Length
                while TempLength:
                    TempLength-=1
                    TempIO(Compress(Loop))
            TempIO(CompressObject.flush(zlib.Z_FINISH))
            del Height,Start,Loop,Compress,CompressObject
            Length=Temp.tell()
            Temp.seek(0)
            TempIO=Temp.read
            #将zlib格式的临时文件变成至少一个IDAT块,并写入png文件(crc32的第二个参数初始值是"IDAT"的crc32值 & 0xffffffff)
            Print("==StartCopy")
            while 2147483647<Length:
                Length-=2147483647
                Write("\x7f\xff\xff\xff" "IDAT")
                CRC=900662814
                TempLength=2147483647
                while BufferSize<TempLength:
                    TempLength-=BufferSize
                    Buffer=TempIO(BufferSize)
                    Write(Buffer)
                    CRC=crc32(Buffer,CRC)
                Buffer=TempIO(TempLength)
                Write(Buffer)
                Write(pack("!I",crc32(Buffer,CRC)&0xffffffff))
            Write(pack("!I",Length))
            Write("IDAT")
            CRC=900662814
            while BufferSize<Length:
                Length-=BufferSize
                Buffer=TempIO(BufferSize)
                Write(Buffer)
                CRC=crc32(Buffer,CRC)
            Buffer=TempIO(Length)
        Write(Buffer)
        Write(pack("!I",crc32(Buffer,CRC)&0xffffffff))
        #IEND(结尾块,无数据)
        Write("\x00\x00\x00\x00" "IEND" "\xae\x42\x60\x82")
    del Buffer,BufferSize,CRC,File,Write,Temp,TempIO,Length,TempLength,crc32,pack,zlib
    #停止
    Print("__stop__")