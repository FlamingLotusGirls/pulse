package org.flg.hiromi.pulsecontroller;

import android.content.Context;
import android.database.sqlite.SQLiteDatabase;
import android.database.sqlite.SQLiteOpenHelper;

/**
 * Created by rwk on 2016-08-18.
 */

public class UDPMessageDBHelper extends SQLiteOpenHelper {
    // If you change the database schema, you must increment the database version.
    public static final int DATABASE_VERSION = 1;
    public static final String DATABASE_NAME = "UDPMessages.db";
    public static final String TABLE_NAME = "messages";
    public static final String FIELD_ID = "_ID";
    public static final String FIELD_TYPE = "type";
    public static final String FIELD_TAG = "tag";
    public static final String FIELD_RECEIVER = "receiver";
    public static final String FIELD_COMMAND= "commmand";
    public static final String FIELD_DATA = "data";

    private static final String SQL_CREATE_TABLES =
            "CREATE TABLE " + TABLE_NAME + " ("
                + FIELD_ID + " INTEGER PRIMARY KEY,"
                + FIELD_TYPE + " TEXT NOT NULL,"
                + FIELD_TAG +  " TEXT UNIQUE,"
                + FIELD_RECEIVER + " INTEGER NOT NULL,"
                + FIELD_COMMAND + " INTEGER NOT NULL,"
                + FIELD_DATA + " INTEGER"
                + ")";

    public UDPMessageDBHelper(Context ctx) {
        super(ctx, DATABASE_NAME, null, DATABASE_VERSION);
    }
    @Override
    public void onCreate(SQLiteDatabase db) {
        db.execSQL(SQL_CREATE_TABLES);
    }

    @Override
    public void onUpgrade(SQLiteDatabase db, int oldVersion, int newVersion) {

    }
}
